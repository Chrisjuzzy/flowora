from datetime import datetime, timedelta
import logging
from typing import Optional, List

from sqlalchemy import func
from sqlalchemy.orm import Session

from models import Agent, Execution, PromptVersion
from services.encryption import encryption_service

logger = logging.getLogger(__name__)


class PromptVersionService:
    @staticmethod
    def _extract_system_prompt(agent: Agent) -> str:
        if not getattr(agent, "config", None):
            return ""
        try:
            config = encryption_service.decrypt_data(agent.config)
        except Exception:
            config = {}
        if isinstance(config, dict):
            return config.get("system_prompt", "") or ""
        if isinstance(config, str):
            return config
        return ""

    @staticmethod
    def ensure_prompt_version(
        db: Session,
        agent: Agent,
        prompt_text: Optional[str] = None,
        source: str = "seed",
        activate_if_missing: bool = True
    ) -> Optional[PromptVersion]:
        prompt_text = prompt_text or PromptVersionService._extract_system_prompt(agent)
        if not prompt_text:
            return None
        existing = (
            db.query(PromptVersion)
            .filter(PromptVersion.agent_id == agent.id, PromptVersion.prompt_text == prompt_text)
            .order_by(PromptVersion.created_at.desc())
            .first()
        )
        if existing:
            return existing

        has_active = (
            db.query(PromptVersion)
            .filter(PromptVersion.agent_id == agent.id, PromptVersion.is_active == True)
            .count()
            > 0
        )
        version = PromptVersion(
            agent_id=agent.id,
            prompt_text=prompt_text,
            source=source,
            is_active=activate_if_missing and not has_active
        )
        db.add(version)
        db.commit()
        db.refresh(version)
        return version

    @staticmethod
    def evaluate_prompt_versions(
        db: Session,
        agent_id: int,
        window_hours: int
    ) -> List[PromptVersion]:
        versions = (
            db.query(PromptVersion)
            .filter(PromptVersion.agent_id == agent_id)
            .order_by(PromptVersion.created_at.asc())
            .all()
        )
        if not versions:
            return []

        cutoff = datetime.utcnow() - timedelta(hours=window_hours)
        for idx, version in enumerate(versions):
            start = max(version.created_at, cutoff)
            end = versions[idx + 1].created_at if idx + 1 < len(versions) else None

            query = db.query(Execution).filter(
                Execution.agent_id == agent_id,
                Execution.timestamp >= start
            )
            if end:
                query = query.filter(Execution.timestamp < end)

            total = query.count()
            successes = query.filter(Execution.status == "completed").count()
            avg_latency = query.with_entities(func.avg(Execution.execution_time_ms)).scalar() or 0

            version.total_runs = total
            version.success_rate = round((successes / total), 3) if total else 0.0
            version.avg_latency_ms = float(avg_latency or 0)
            version.last_evaluated_at = datetime.utcnow()

        db.commit()
        return versions

    @staticmethod
    def select_best_version(versions: List[PromptVersion], min_runs: int) -> Optional[PromptVersion]:
        candidates = [v for v in versions if v.total_runs >= min_runs]
        if not candidates:
            return None
        return max(
            candidates,
            key=lambda v: (v.success_rate, v.total_runs, -v.avg_latency_ms)
        )

    @staticmethod
    def activate_prompt_version(db: Session, agent: Agent, version: PromptVersion) -> None:
        if not version:
            return
        db.query(PromptVersion).filter(
            PromptVersion.agent_id == agent.id,
            PromptVersion.id != version.id,
            PromptVersion.is_active == True
        ).update({PromptVersion.is_active: False})
        version.is_active = True

        try:
            config = encryption_service.decrypt_data(agent.config) if agent.config else {}
        except Exception:
            config = {}
        if not isinstance(config, dict):
            config = {}
        config["system_prompt"] = version.prompt_text
        agent.config = encryption_service.encrypt_data(config)

        db.commit()

    @staticmethod
    def rollback_if_degraded(
        db: Session,
        agent: Agent,
        versions: List[PromptVersion],
        min_runs: int,
        threshold: float
    ) -> Optional[PromptVersion]:
        active = next((v for v in versions if v.is_active), None)
        if not active:
            return None

        if active.source != "auto":
            return None

        if active.total_runs < min_runs:
            return None

        if active.success_rate >= threshold:
            return None

        previous_versions = [
            v for v in versions
            if v.created_at < active.created_at and v.total_runs >= min_runs
        ]
        if not previous_versions:
            return None

        best_previous = max(
            previous_versions,
            key=lambda v: (v.success_rate, v.total_runs, -v.avg_latency_ms)
        )
        active.notes = f"Auto-rollback triggered at {datetime.utcnow().isoformat()}"
        PromptVersionService.activate_prompt_version(db, agent, best_previous)
        return best_previous

    @staticmethod
    def get_active_prompt(db: Session, agent: Agent, fallback_prompt: Optional[str] = None) -> Optional[PromptVersion]:
        active = (
            db.query(PromptVersion)
            .filter(PromptVersion.agent_id == agent.id, PromptVersion.is_active == True)
            .order_by(PromptVersion.created_at.desc())
            .first()
        )
        if active:
            return active
        if fallback_prompt:
            return PromptVersionService.ensure_prompt_version(db, agent, fallback_prompt, source="seed", activate_if_missing=True)
        return None
