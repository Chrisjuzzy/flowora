from sqlalchemy.orm import Session
from models import UsageLog
from datetime import datetime
import logging
from services.wallet_service import (
    InsufficientBalanceError,
    debit_wallet,
    get_or_create_wallet,
    serialize_amount,
)

logger = logging.getLogger(__name__)


def record_usage(
    db: Session,
    user_id: int,
    execution_type: str,
    cost: float = 0.0,
    tokens_used: int = 0,
    compute_time_ms: int = 0,
    agent_id: int | None = None,
    workflow_id: int | None = None,
    swarm_id: str | None = None,
    enforce_balance: bool = False,
) -> UsageLog:
    usage = UsageLog(
        user_id=user_id,
        agent_id=agent_id,
        workflow_id=workflow_id,
        swarm_id=swarm_id,
        execution_type=execution_type,
        compute_time_ms=compute_time_ms,
        tokens_used=tokens_used,
        cost=cost
    )
    db.add(usage)

    if cost and cost > 0:
        wallet = get_or_create_wallet(db, user_id)
        try:
            wallet, _ = debit_wallet(
                db=db,
                user_id=user_id,
                amount=cost,
                transaction_type="usage_billing",
                description=f"{execution_type} usage",
                reference_id=f"usage_{int(datetime.utcnow().timestamp())}",
                currency=wallet.currency,
            )
            logger.info(
                "Usage billed",
                extra={"user_id": user_id, "wallet_id": wallet.id, "amount": -float(cost), "type": execution_type}
            )
        except InsufficientBalanceError:
            if enforce_balance:
                raise
            logger.info(
                "Usage logged without wallet debit",
                extra={
                    "user_id": user_id,
                    "wallet_id": wallet.id,
                    "requested_amount": float(cost),
                    "wallet_balance": serialize_amount(wallet.balance),
                    "type": execution_type
                }
            )

    db.commit()
    db.refresh(usage)
    return usage
