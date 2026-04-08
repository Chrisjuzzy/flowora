from datetime import datetime
from typing import Optional
import logging

from fastapi import HTTPException

from services.agent_runtime.models import RuntimeResult
from services.agent_runtime.execution_logger import ExecutionLogger
from services.agent_runtime.tools import ToolRegistry, tool_registry as default_tool_registry
from services.agent_runtime.memory import DefaultMemoryProvider, MemoryProvider
from services.agent_runtime.brain import AgentBrain
from services.ai_provider_service import AIProviderFactory
from config_production import settings
from services.ai_limiter import ollama_limiter
from services.encryption import encryption_service
from services.sandbox import sandbox_service
from services.self_improvement_service import SelfImprovementService
from services.intelligence_service import ReflectionService
from services.tool_permissions import ToolPermissionService
from services.prompt_version_service import PromptVersionService
from models import Agent, Execution, AgentRun
from utils.watermark import apply_flowora_watermark

logger = logging.getLogger(__name__)


class AgentRuntime:
    def __init__(self, tool_registry: Optional[ToolRegistry] = None, memory_provider: Optional[MemoryProvider] = None):
        self.tool_registry = tool_registry or default_tool_registry
        self.memory_provider = memory_provider or DefaultMemoryProvider()

    async def execute(
        self,
        db,
        agent_id: int,
        input_data: Optional[str] = None,
        simulation_mode: bool = False,
        user_id: Optional[int] = None,
        max_steps: int = 1
    ):
        """
        Agent execution pipeline:
        1. Load agent configuration
        2. Retrieve memory context
        3. Run reasoning loop (single-step by default)
        4. Execute tool calls (if provided by provider/tool registry)
        5. Store execution logs
        """
        agent = db.query(Agent).filter(Agent.id == agent_id).first()
        if not agent:
            raise ValueError(f"Agent with id {agent_id} not found")

        # Sandbox: input validation
        if input_data:
            validation = sandbox_service.validate_execution_request(db, agent_id, user_id, input_data)
            if not validation["valid"]:
                return {"status": "blocked", "error": validation["error"]}

        # Build prompts
        system_prompt = "You are a helpful AI assistant."
        user_prompt = f"Act as an agent with the following description: {agent.description}. Please perform your task."

        agent_config = {}
        if getattr(agent, "config", None):
            try:
                agent_config = encryption_service.decrypt_data(agent.config)
            except Exception as exc:
                logger.warning("Failed to decrypt agent config: %s", exc)
                agent_config = {}

        if "system_prompt" in agent_config:
            system_prompt = agent_config["system_prompt"]
        if "prompt" in agent_config:
            user_prompt = agent_config["prompt"]

        prompt_version_id = None
        try:
            active_prompt = PromptVersionService.get_active_prompt(db, agent, system_prompt)
            if active_prompt and active_prompt.prompt_text:
                system_prompt = active_prompt.prompt_text
                prompt_version_id = active_prompt.id
        except Exception as exc:
            logger.warning("Prompt version lookup failed: %s", exc)

        if input_data:
            if "{input}" in user_prompt:
                user_prompt = user_prompt.replace("{input}", input_data)
            elif "{url}" in user_prompt:
                user_prompt = user_prompt.replace("{url}", input_data)
            else:
                user_prompt += f"\n\nInput: {input_data}"

        result = RuntimeResult(status="completed", output="")
        started_at = datetime.utcnow()
        exec_logger = None

        try:
            provider_name = agent.ai_provider or settings.DEFAULT_AI_PROVIDER
            ai_provider = AIProviderFactory.get_provider(provider_name)

            allowed_tools = ToolPermissionService.get_allowed_tools(db, agent_id)
            if not allowed_tools and isinstance(agent_config, dict) and agent_config.get("tools"):
                tools_value = agent_config.get("tools")
                if isinstance(tools_value, str):
                    allowed_tools = [t.strip() for t in tools_value.split(",") if t.strip()]
                elif isinstance(tools_value, list):
                    allowed_tools = [str(t).strip() for t in tools_value if str(t).strip()]

            effective_max_steps = max_steps
            if isinstance(agent_config, dict) and agent_config.get("max_steps"):
                try:
                    effective_max_steps = int(agent_config.get("max_steps", max_steps))
                except Exception:
                    effective_max_steps = max_steps

            if not allowed_tools and effective_max_steps <= 2:
                provider_result = await ollama_limiter.run(
                    lambda: ai_provider.generate_with_metadata(
                        user_prompt,
                        system_prompt=system_prompt,
                        model=agent.model_name or settings.DEFAULT_AI_MODEL,
                        temperature=agent.temperature
                    )
                )
                result = RuntimeResult(
                    status="completed",
                    output=provider_result.get("text", ""),
                    token_usage=provider_result.get("token_usage", 0) or 0,
                    execution_time_ms=provider_result.get("execution_time_ms", 0) or 0,
                    cost_estimate=str(provider_result.get("cost_estimate", "0.0") or "0.0")
                )
                exec_logger = ExecutionLogger()
                exec_logger.log(1, "final", "Generated direct response", {"output": result.output})
            else:
                brain = AgentBrain(self.tool_registry, self.memory_provider)
                result, exec_logger = await ollama_limiter.run(
                    lambda: brain.run(
                        db=db,
                        provider=ai_provider,
                        agent_id=agent_id,
                        goal=user_prompt,
                        system_prompt=system_prompt,
                        model=agent.model_name or settings.DEFAULT_AI_MODEL,
                        temperature=agent.temperature,
                        max_steps=effective_max_steps,
                        allowed_tools=allowed_tools
                    )
                )

            # Sandbox: output validation
            validation = sandbox_service.validate_execution_result(db, agent_id, result.output)
            if not validation["valid"]:
                return {"status": "blocked", "error": validation["error"]}

            result.output = apply_flowora_watermark(result.output)

            if not simulation_mode:
                execution = Execution(
                    agent_id=agent_id,
                    user_id=user_id,
                    prompt_version_id=prompt_version_id,
                    status="completed",
                    result=result.output,
                    token_usage=result.token_usage,
                    execution_time_ms=result.execution_time_ms,
                    cost_estimate=result.cost_estimate
                )
                db.add(execution)

                agent_run = AgentRun(
                    agent_id=agent_id,
                    prompt_version_id=prompt_version_id,
                    input_prompt=input_data or user_prompt,
                    output_response=result.output,
                    execution_time=result.execution_time_ms
                )
                db.add(agent_run)
                db.commit()
                db.refresh(execution)
                db.refresh(agent_run)
                execution.agent_run_id = agent_run.id

                try:
                    if exec_logger:
                        exec_logger.persist(db, execution.id, agent_id, prompt_version_id=prompt_version_id)
                except Exception as exc:
                    logger.warning("Execution log persist failed: %s", exc)

                try:
                    SelfImprovementService.write_agent_memory(
                        db=db,
                        agent_id=agent_id,
                        input_prompt=input_data or user_prompt,
                        output_response=result.output,
                        execution_time=result.execution_time_ms
                    )
                except Exception as exc:
                    logger.warning("Failed to write agent memory: %s", exc)

                try:
                    self.memory_provider.store_memory(db, agent_id, input_data, result.output, success_rating=8)
                except Exception as exc:
                    logger.warning("Memory store failed: %s", exc)

                if input_data:
                    ReflectionService.schedule_reflection(
                        agent_id=agent_id,
                        execution_id=execution.id,
                        input_data=input_data,
                        result=result.output,
                    )

                return execution

            return {
                "status": "simulated",
                "result": result.output,
                "token_usage": result.token_usage,
                "cost_estimate": result.cost_estimate,
                "plan": [step.description for step in result.plan],
                "logs": [entry.message for entry in result.logs]
            }
        except HTTPException as exc:
            if exc.status_code in (429, 504):
                logger.info("Agent runtime ended with expected HTTP exception: %s", exc.detail)
            else:
                logger.warning("Agent runtime HTTP exception: %s", exc.detail, exc_info=True)
            if not simulation_mode:
                failed_execution = Execution(
                    agent_id=agent_id,
                    prompt_version_id=prompt_version_id,
                    status="failed",
                    result=str(exc.detail)
                )
                db.add(failed_execution)
                db.commit()
            raise
        except Exception as exc:
            logger.error("Agent runtime failed: %s", exc, exc_info=True)
            if not simulation_mode:
                failed_execution = Execution(
                    agent_id=agent_id,
                    prompt_version_id=prompt_version_id,
                    status="failed",
                    result=str(exc)
                )
                db.add(failed_execution)
                db.commit()
            raise
        finally:
            result.finished_at = datetime.utcnow()
            result.started_at = started_at


default_runtime = AgentRuntime()
