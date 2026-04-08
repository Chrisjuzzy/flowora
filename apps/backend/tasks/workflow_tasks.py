import asyncio
from typing import Any, Dict

from celery_app import celery_app
from database_production import get_db_context
from services.workflow_runner import run_workflow
from services.execution_policy import record_successful_execution
from models import User


def _run_async(coro):
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            return asyncio.run(coro)
    except RuntimeError:
        pass
    return asyncio.run(coro)


@celery_app.task(name="tasks.workflow_tasks.run_workflow")
def run_workflow_task(payload: Dict[str, Any]):
    workflow_id = payload.get("workflow_id")
    input_data = payload.get("input_data")
    user_id = payload.get("user_id")
    with get_db_context() as db:
        result = _run_async(run_workflow(db, workflow_id, initial_input=input_data))
        if user_id:
            user = db.query(User).filter(User.id == user_id).first()
            if user:
                record_successful_execution(user, db, tokens_used=0)
        return result
