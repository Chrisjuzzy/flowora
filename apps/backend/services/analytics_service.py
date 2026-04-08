from typing import Dict, List
from sqlalchemy.orm import Session
from sqlalchemy import func

from models import Execution, ExecutionLog, PromptVersion


class AnalyticsService:
    @staticmethod
    def agent_success_rate(db: Session, agent_id: int) -> Dict[str, float]:
        total = db.query(func.count(Execution.id)).filter(Execution.agent_id == agent_id).scalar() or 0
        success = db.query(func.count(Execution.id)).filter(
            Execution.agent_id == agent_id,
            Execution.status == "completed"
        ).scalar() or 0
        rate = (success / total) if total else 0.0
        return {"agent_id": agent_id, "total": total, "success": success, "success_rate": round(rate, 3)}

    @staticmethod
    def tool_performance(db: Session, agent_id: int) -> List[Dict[str, any]]:
        logs = db.query(ExecutionLog).filter(
            ExecutionLog.agent_id == agent_id,
            ExecutionLog.phase == "tool"
        ).all()
        counts: Dict[str, int] = {}
        for log in logs:
            tool_name = "unknown"
            if log.payload and "\"tool\"" in log.payload:
                try:
                    import json
                    payload = json.loads(log.payload)
                    tool_name = payload.get("tool", tool_name)
                except Exception:
                    pass
            counts[tool_name] = counts.get(tool_name, 0) + 1
        return [{"tool": tool, "calls": count} for tool, count in sorted(counts.items(), key=lambda x: x[1], reverse=True)]

    @staticmethod
    def task_completion(db: Session) -> Dict[str, float]:
        total = db.query(func.count(Execution.id)).scalar() or 0
        completed = db.query(func.count(Execution.id)).filter(Execution.status == "completed").scalar() or 0
        return {
            "total_executions": total,
            "completed": completed,
            "completion_rate": round((completed / total) if total else 0.0, 3)
        }

    @staticmethod
    def prompt_performance(db: Session, agent_id: int):
        versions = db.query(PromptVersion).filter(
            PromptVersion.agent_id == agent_id
        ).order_by(PromptVersion.created_at.desc()).all()
        return [
            {
                "id": v.id,
                "agent_id": v.agent_id,
                "prompt_text": v.prompt_text,
                "success_rate": v.success_rate,
                "total_runs": v.total_runs,
                "avg_latency_ms": v.avg_latency_ms,
                "is_active": v.is_active,
                "source": v.source,
                "notes": v.notes,
                "created_at": v.created_at,
                "last_evaluated_at": v.last_evaluated_at
            }
            for v in versions
        ]
