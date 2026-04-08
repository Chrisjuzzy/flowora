import asyncio
from typing import Any, Dict

from celery_app import celery_app
from database_production import get_db_context
from services.agent_runner import run_agent
from services.execution_policy import record_successful_execution
from services.usage_billing import record_usage
from models import User, Wallet
from services.wallet_service import serialize_amount


def _run_async(coro):
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            return asyncio.run(coro)
    except RuntimeError:
        pass
    return asyncio.run(coro)


@celery_app.task(name="tasks.agent_tasks.execute_agent")
def execute_agent(payload: Dict[str, Any]):
    agent_id = payload.get("agent_id")
    input_data = payload.get("input_data")
    user_id = payload.get("user_id")
    with get_db_context() as db:
        execution = _run_async(run_agent(db, agent_id, input_data=input_data, user_id=user_id))
        if hasattr(execution, "id"):
            # Post execution accounting
            user = db.query(User).filter(User.id == user_id).first()
            if user:
                record_successful_execution(user, db, tokens_used=execution.token_usage if execution.token_usage else 0)
                record_usage(
                    db=db,
                    user_id=user.id,
                    execution_type="agent_run",
                    cost=1.0,
                    tokens_used=execution.token_usage if execution.token_usage else 0,
                    compute_time_ms=execution.execution_time_ms if getattr(execution, "execution_time_ms", None) else 0,
                    agent_id=agent_id
                )
            wallet = db.query(Wallet).filter(Wallet.user_id == user_id).first()
            return {
                "status": "completed",
                "execution_id": execution.id,
                "remaining_credits": serialize_amount(wallet.balance) if wallet else None
            }
        return execution
