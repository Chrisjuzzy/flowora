import logging
from typing import Dict, Optional, Tuple

from sqlalchemy.orm import Session
from sqlalchemy import func

from models import Agent, AgentVersion, Execution, ExecutionLog
from services.ai_provider_service import AIProviderFactory
from services.encryption import encryption_service
from services.prompt_version_service import PromptVersionService

logger = logging.getLogger(__name__)


def _bump_patch(version: str) -> str:
    try:
        parts = [int(p) for p in version.split(".")]
        if len(parts) < 3:
            parts = (parts + [0, 0, 0])[:3]
        parts[2] += 1
        return f"{parts[0]}.{parts[1]}.{parts[2]}"
    except Exception:
        return "1.0.1"


class AgentOptimizer:
    def __init__(self, provider_name: str = "openai") -> None:
        self.provider_name = provider_name

    def _collect_metrics(self, db: Session, agent_id: int) -> Dict[str, float]:
        total = db.query(func.count(Execution.id)).filter(Execution.agent_id == agent_id).scalar() or 0
        successes = db.query(func.count(Execution.id)).filter(
            Execution.agent_id == agent_id,
            Execution.status == "completed"
        ).scalar() or 0
        failures = total - successes
        avg_latency = db.query(func.avg(Execution.execution_time_ms)).filter(
            Execution.agent_id == agent_id
        ).scalar() or 0

        tool_calls = db.query(func.count(ExecutionLog.id)).filter(
            ExecutionLog.agent_id == agent_id,
            ExecutionLog.phase == "tool"
        ).scalar() or 0

        success_rate = (successes / total) if total > 0 else 0.0
        return {
            "total_runs": total,
            "success_rate": round(success_rate, 3),
            "failures": failures,
            "avg_latency_ms": float(avg_latency or 0),
            "tool_calls": int(tool_calls)
        }

    async def optimize_agent_prompt(
        self,
        db: Session,
        agent_id: int,
        min_runs: int = 5,
        failure_summary: Optional[str] = None
    ) -> Tuple[Optional[Agent], Dict[str, float]]:
        agent = db.query(Agent).filter(Agent.id == agent_id).first()
        if not agent:
            return None, {}

        metrics = self._collect_metrics(db, agent_id)
        if metrics.get("total_runs", 0) < min_runs:
            return agent, metrics

        config = {}
        if agent.config:
            try:
                config = encryption_service.decrypt_data(agent.config)
            except Exception:
                config = {}

        current_prompt = ""
        if isinstance(config, dict):
            current_prompt = config.get("system_prompt", "")

        if current_prompt:
            try:
                PromptVersionService.ensure_prompt_version(db, agent, current_prompt, source="seed", activate_if_missing=True)
            except Exception as exc:
                logger.warning("Prompt version seed failed: %s", exc)

        provider = AIProviderFactory.get_provider(self.provider_name)
        prompt = (
            "Improve the following system prompt based on the metrics. "
            "Return only the improved prompt text.\n\n"
            f"Metrics: {metrics}\n"
        )
        if failure_summary:
            prompt += f"Failure signals: {failure_summary}\n"
        prompt += f"Current prompt: {current_prompt}"
        try:
            response = await provider.generate_with_metadata(prompt)
            improved_prompt = response.get("text", "").strip()
        except Exception as exc:
            logger.warning("Prompt optimization failed: %s", exc)
            improved_prompt = current_prompt

        if not improved_prompt:
            improved_prompt = current_prompt

        if isinstance(config, dict):
            config["system_prompt"] = improved_prompt
            config["optimization_metrics"] = metrics

        new_version = _bump_patch(agent.version or "1.0.0")
        agent.version = new_version
        agent.config = encryption_service.encrypt_data(config)

        db.add(
            AgentVersion(
                agent_id=agent.id,
                version=new_version,
                config=config,
                description="Auto-optimized prompt"
            )
        )

        try:
            if improved_prompt and improved_prompt != current_prompt:
                PromptVersionService.ensure_prompt_version(
                    db,
                    agent,
                    improved_prompt,
                    source="auto",
                    activate_if_missing=True
                )
        except Exception as exc:
            logger.warning("Prompt version creation failed: %s", exc)

        db.commit()
        db.refresh(agent)
        return agent, metrics
