import asyncio
from typing import Any, Dict

from celery_app import celery_app
from database_production import get_db_context
from services.workflow_runner import run_swarm


def _run_async(coro):
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            return asyncio.run(coro)
    except RuntimeError:
        pass
    return asyncio.run(coro)


@celery_app.task(name="tasks.swarm_tasks.run_swarm")
def run_swarm_task(payload: Dict[str, Any]):
    agent_ids = payload.get("agent_ids") or []
    goal = payload.get("goal") or ""
    workspace_id = payload.get("workspace_id")
    max_rounds = payload.get("max_rounds", 3)
    with get_db_context() as db:
        result = _run_async(run_swarm(db, agent_ids, goal, workspace_id, max_rounds))
        return {"status": "completed", "result": result}
