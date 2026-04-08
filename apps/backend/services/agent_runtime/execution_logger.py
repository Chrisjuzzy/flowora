import json
import logging
from typing import Any, Dict, List, Optional

from sqlalchemy.exc import SQLAlchemyError

from services.agent_runtime.models import ExecutionLogEntry
from models import ExecutionLog

logger = logging.getLogger(__name__)


class ExecutionLogger:
    def __init__(self) -> None:
        self.entries: List[ExecutionLogEntry] = []

    def log(self, step: int, phase: str, message: str, data: Optional[Dict[str, Any]] = None) -> None:
        self.entries.append(
            ExecutionLogEntry(step=step, phase=phase, message=message, data=data or {})
        )

    def to_dict(self) -> List[Dict[str, Any]]:
        return [
            {
                "step": entry.step,
                "phase": entry.phase,
                "message": entry.message,
                "data": entry.data,
                "timestamp": entry.timestamp.isoformat()
            }
            for entry in self.entries
        ]

    def persist(self, db, execution_id: int, agent_id: int, prompt_version_id: Optional[int] = None) -> None:
        if not self.entries:
            return
        try:
            for entry in self.entries:
                log = ExecutionLog(
                    execution_id=execution_id,
                    agent_id=agent_id,
                    prompt_version_id=prompt_version_id,
                    step=entry.step,
                    phase=entry.phase,
                    message=entry.message,
                    payload=json.dumps(entry.data) if entry.data else None
                )
                db.add(log)
            db.commit()
        except SQLAlchemyError as exc:
            logger.warning("Execution log persistence failed: %s", exc)
            db.rollback()
