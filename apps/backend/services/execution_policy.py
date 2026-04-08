"""
Unified Execution Policy Service

Central gatekeeper for agent/workflow execution.
Enforces subscription, usage limits, email verification, and credit allocation.

This is the single enforcement point for ALL agent/workflow executions.
"""

from fastapi import HTTPException
from sqlalchemy.orm import Session
from models.user import User
from models.monetization import Wallet
from services.credit_system import CreditSystem
from routers.billing import TIER_LIMITS
import logging
from config_production import settings
from services.wallet_service import normalize_amount, serialize_amount

logger = logging.getLogger(__name__)


def _is_truthy(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() in {"true", "1", "yes", "y"}
    return False


def enforce_execution_policy(
    user: User,
    db: Session,
    agent_type: str = None  # Optional: agent type to check specific cost
) -> None:
    """
    PRE-EXECUTION GATE: Unified enforcement before agent/workflow runs.
    
    Checks (in order):
    1. Email is verified
    2. Subscription status is "active"
    3. Monthly execution limit not exceeded
    4. Sufficient credits available (if using credit system)
    5. Wallet has sufficient balance (legacy compatibility)
    
    Raises HTTPException if ANY check fails.
    Does NOT modify user state.
    
    Args:
        user: Current user object
        db: Database session
        agent_type: Optional agent type (e.g., "lead_generator") to check specific cost
        
    Raises:
        HTTPException(403): Email not verified or subscription inactive
        HTTPException(429): Execution limit reached or insufficient credits
        HTTPException(402): Insufficient funds/credits
    """
    
    # Check 1: Email verification
    if settings.EMAIL_VERIFICATION_REQUIRED and not _is_truthy(user.is_email_verified):
        raise HTTPException(
            status_code=403,
            detail="Please verify your email before executing agents."
        )
    
    # Check 2: Subscription status
    if user.subscription_status != "active":
        raise HTTPException(
            status_code=403,
            detail="Subscription not active. Please renew to continue."
        )
    
    # Check 3: Monthly execution limit (from billing.py TIER_LIMITS)
    tier = user.subscription_tier or "free"
    limit = TIER_LIMITS.get(tier, {}).get("runs_per_month", 50)
    
    if user.executions_this_month >= limit:
        raise HTTPException(
            status_code=429,
            detail=f"{tier.capitalize()} plan: {limit} executions/month limit reached. Upgrade to continue."
        )
    
    # Check 4: Credit allocation (NEW - credit-based system)
    # If enterprise tier, skip credit check (unlimited credits)
    if tier != "enterprise":
        required_credits = 1  # Default
        if agent_type:
            required_credits = CreditSystem.get_agent_cost(agent_type)
        
        available_credits = CreditSystem.get_available_credits_this_month(user, db)
        
        if available_credits < required_credits:
            raise HTTPException(
                status_code=429,
                detail=f"Insufficient credits. You have {available_credits} credits "
                       f"but this agent requires {required_credits}. "
                       f"Upgrade your plan to continue."
            )
    
    # Check 5: Wallet balance (legacy wallet system - for marketplace purchases, etc.)
    wallet = db.query(Wallet).filter(Wallet.user_id == user.id).first()
    cost_per_execution = normalize_amount(1.0)  # Default cost per execution in wallet
    current_balance = normalize_amount(wallet.balance) if wallet is not None else normalize_amount(0)

    if wallet is None or current_balance < cost_per_execution:
        # Log warning but don't block (wallet system is legacy)
        logger.warning(
            f"User {user.id} has low wallet balance ({serialize_amount(current_balance)}) "
            f"but can execute with credit system"
        )
    
    logger.info(f"Execution policy passed for user {user.id} (tier={tier}, agent_type={agent_type})")


def record_successful_execution(
    user: User,
    db: Session,
    tokens_used: int = 0,
    agent_type: str = None,
    execution_id: str = None
) -> None:
    """
    POST-EXECUTION RECORD: Update usage metrics after successful run.
    
    ONLY called if agent/workflow execution completes successfully.
    Rolls back on any error to maintain data integrity.
    
    Updates:
    - Monthly execution counter
    - Monthly token counter
    - Credit deduction (if using credit system)
    
    Args:
        user: Current user object
        db: Database session
        tokens_used: Number of tokens consumed (default 0)
        agent_type: Type of agent executed (for credit deduction)
        execution_id: Execution ID for reference tracking
        
    Raises:
        HTTPException(500): If database commit fails
    """
    try:
        # Increment execution counters (monthly usage)
        user.executions_this_month += 1
        user.tokens_used_this_month += tokens_used
        
        # Deduct credits from monthly allocation (if not enterprise)
        tier = user.subscription_tier or "free"
        if tier != "enterprise" and agent_type:
            cost = CreditSystem.get_agent_cost(agent_type)
            execution_id_str = str(execution_id) if execution_id else "unknown"
            
            CreditSystem.deduct_credits(
                user=user,
                db=db,
                amount=cost,
                agent_type=agent_type,
                execution_id=execution_id_str
            )
        
        # Commit atomically
        db.commit()
        
        logger.info(
            f"Recorded execution for user {user.id}: "
            f"executions={user.executions_this_month}, "
            f"tokens={user.tokens_used_this_month}, "
            f"agent_type={agent_type}"
        )
    
    except Exception as e:
        # Rollback on any database error
        db.rollback()
        logger.error(f"Failed to record execution for user {user.id}: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to record execution. Please try again."
        )
