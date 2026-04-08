import asyncio
from typing import Any, Dict

from celery_app import celery_app
from database_production import get_db_context
from services.agent_optimizer import AgentOptimizer


def _run_async(coro):
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            return asyncio.run(coro)
    except RuntimeError:
        pass
    return asyncio.run(coro)


@celery_app.task(name="tasks.optimization_tasks.optimize_agent")
def optimize_agent(payload: Dict[str, Any]):
    agent_id = payload.get("agent_id")
    min_runs = payload.get("min_runs", 5)
    optimizer = AgentOptimizer()
    with get_db_context() as db:
        agent, metrics = _run_async(optimizer.optimize_agent_prompt(db, agent_id, min_runs=min_runs))
        if not agent:
            return {"status": "not_found", "agent_id": agent_id}
        return {
            "status": "optimized",
            "agent_id": agent.id,
            "version": agent.version,
            "metrics": metrics
        }
