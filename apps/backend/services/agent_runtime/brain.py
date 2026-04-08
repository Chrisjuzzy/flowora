import json
import logging
from typing import Any, Dict, List, Optional

from services.agent_runtime.execution_logger import ExecutionLogger
from services.agent_runtime.memory import MemoryProvider
from services.agent_runtime.models import PlanStep, RuntimeResult, ToolCall
from services.agent_runtime.planner import PlanGenerator

logger = logging.getLogger(__name__)


def _extract_json_object(text: str) -> Optional[dict]:
    if not text:
        return None
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    try:
        return json.loads(text[start : end + 1])
    except Exception:
        return None


class AgentBrain:
    def __init__(
        self,
        tool_registry,
        memory_provider: MemoryProvider,
        planner: Optional[PlanGenerator] = None
    ) -> None:
        self.tool_registry = tool_registry
        self.memory_provider = memory_provider
        self.planner = planner or PlanGenerator()

    def _format_tools(self, allowed: Optional[List[str]] = None) -> str:
        tools = self.tool_registry.list_tools()
        lines = []
        for name, tool in tools.items():
            if allowed and name not in allowed:
                continue
            schema = json.dumps(tool.input_schema)
            lines.append(f"- {name}: {tool.description}. Input schema: {schema}")
        return "\n".join(lines)

    def _build_reasoning_prompt(
        self,
        goal: str,
        plan_step: PlanStep,
        memory_context: str,
        scratchpad: List[str],
        tool_block: str
    ) -> str:
        scratch = "\n".join(scratchpad[-8:]) if scratchpad else "none"
        prompt = (
            "You are an autonomous agent. Follow the plan step and decide whether to use a tool.\n"
            "Return a JSON object with keys: "
            "`analysis` (string), "
            "`action` (object or null with fields `tool` and `args`), "
            "`final` (string or null).\n\n"
            f"Goal: {goal}\n"
            f"Current step: {plan_step.step}. {plan_step.description}\n"
            f"Expected output: {plan_step.expected_output or 'unspecified'}\n\n"
            f"Memory context:\n{memory_context or 'none'}\n\n"
            f"Scratchpad:\n{scratch}\n\n"
            f"Available tools:\n{tool_block or 'none'}"
        )
        return prompt

    async def _evaluate(
        self,
        provider,
        goal: str,
        output: str,
        system_prompt: str,
        model: Optional[str],
        temperature: Optional[float]
    ) -> Dict[str, Any]:
        prompt = (
            "Evaluate whether the output satisfies the goal. "
            "Return JSON with keys: `goal_achieved` (boolean) and `notes` (string).\n\n"
            f"Goal: {goal}\n"
            f"Output: {output}"
        )
        try:
            response = await provider.generate_with_metadata(
                prompt,
                system_prompt=system_prompt,
                model=model,
                temperature=temperature
            )
            data = _extract_json_object(response.get("text", ""))
            if isinstance(data, dict):
                return {
                    "goal_achieved": bool(data.get("goal_achieved", False)),
                    "notes": data.get("notes", "")
                }
        except Exception as exc:
            logger.warning("Evaluation failed: %s", exc)
        return {"goal_achieved": bool(output), "notes": "Heuristic evaluation"}

    async def run(
        self,
        db,
        provider,
        agent_id: int,
        goal: str,
        system_prompt: str,
        model: Optional[str],
        temperature: Optional[float],
        max_steps: int,
        allowed_tools: Optional[List[str]] = None
    ) -> RuntimeResult:
        result = RuntimeResult(status="running", output="")
        exec_logger = ExecutionLogger()

        memory_context = self.memory_provider.retrieve_context(db, agent_id, goal)
        tool_block = self._format_tools(allowed_tools)

        plan = await self.planner.build_plan(provider, goal, system_prompt, allowed_tools)
        result.plan = plan
        exec_logger.log(0, "plan", "Generated execution plan", {"steps": [p.description for p in plan]})

        scratchpad: List[str] = []
        output_text = ""
        total_tokens = 0
        total_time = 0
        total_cost = 0.0

        for idx, plan_step in enumerate(plan[:max_steps], start=1):
            prompt = self._build_reasoning_prompt(goal, plan_step, memory_context, scratchpad, tool_block)
            exec_logger.log(idx, "reasoning", "Prompted reasoning step", {"step": plan_step.description})

            provider_result = await provider.generate_with_metadata(
                prompt,
                system_prompt=system_prompt,
                model=model,
                temperature=temperature
            )
            raw_text = provider_result.get("text", "")
            total_tokens += provider_result.get("token_usage", 0) or 0
            total_time += provider_result.get("execution_time_ms", 0) or 0
            total_cost += float(provider_result.get("cost_estimate", "0") or 0)

            parsed = _extract_json_object(raw_text)
            if not parsed:
                output_text = raw_text
                exec_logger.log(idx, "final", "Produced final response (plain text)", {"output": output_text})
                break

            action = parsed.get("action") or {}
            final = parsed.get("final")

            if action and action.get("tool"):
                tool_name = str(action.get("tool"))
                tool_args = action.get("args") or {}
                if allowed_tools and tool_name not in allowed_tools:
                    observation = f"Tool '{tool_name}' not permitted."
                    exec_logger.log(idx, "tool", "Blocked tool call", {"tool": tool_name})
                else:
                    try:
                        tool_result = self.tool_registry.execute(
                            tool_name,
                            tool_args,
                            context={"db": db, "agent_id": agent_id}
                        )
                        observation = json.dumps(tool_result)
                        result.tool_calls.append(ToolCall(name=tool_name, arguments=tool_args))
                        exec_logger.log(idx, "tool", "Executed tool", {"tool": tool_name, "result": tool_result})
                    except Exception as exc:
                        observation = f"Tool error: {exc}"
                        exec_logger.log(idx, "tool", "Tool execution failed", {"tool": tool_name, "error": str(exc)})

                scratchpad.append(f"Observation: {observation}")
                output_text = final or output_text
            else:
                output_text = final or parsed.get("analysis", "") or raw_text
                exec_logger.log(idx, "reasoning", "Reasoning response", {"output": output_text})

            if output_text:
                evaluation = await self._evaluate(provider, goal, output_text, system_prompt, model, temperature)
                exec_logger.log(idx, "evaluation", "Evaluation completed", evaluation)
                if evaluation.get("goal_achieved"):
                    exec_logger.log(idx, "final", "Goal achieved", {"output": output_text})
                    break
                scratchpad.append(f"Evaluation notes: {evaluation.get('notes', '')}")

        result.status = "completed" if output_text else "incomplete"
        result.output = output_text
        result.token_usage = total_tokens
        result.execution_time_ms = total_time
        result.cost_estimate = f"{total_cost:.6f}"
        result.logs = exec_logger.entries
        return result, exec_logger
