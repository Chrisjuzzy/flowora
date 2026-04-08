"""
=====================================
CREDIT SYSTEM SERVICE
=====================================

Manages credit-based system for agent executions.

Credit Allocations (per month):
- free: 20 credits
- pro: 500 credits
- enterprise: unlimited

Each agent has an execution cost in credits:
- leadershipgenerator: 1 credit
- social_content: 1 credit
- offer_optimizer: 2 credits
"""

from sqlalchemy.orm import Session
from models.user import User
from models.monetization import CreditTransaction
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


# Standalone wrapper functions for backward compatibility
def get_user_credit_balance(db: Session, user_id: int) -> int:
    """
    Get current credit balance for a user.
    
    Args:
        db: Database session
        user_id: User ID
    
    Returns:
        Available credits
    """
    from models.user import User
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return 0
    return CreditSystem.get_available_credits_this_month(user, db)


def deduct_credits(db: Session, user_id: int, amount: int, agent_type: str, execution_id: str = None, transaction_type: str = "agent_execution") -> bool:
    """
    Deduct credits from user's account.
    
    Args:
        db: Database session
        user_id: User ID
        amount: Number of credits to deduct
        agent_type: Type of agent being executed
        transaction_type: Type of transaction
    
    Returns:
        True if successful, False otherwise
    """
    from models.user import User
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return False
    return CreditSystem.deduct_credits(user, db, amount, agent_type, execution_id or "unknown")


# Credit allocations per subscription tier (monthly)
CREDIT_LIMITS = {
    "free": 20,
    "pro": 500,
    "enterprise": float("inf")  # Unlimited
}

# Agent execution costs (in credits)
AGENT_COSTS = {
    "lead_generator": 1,
    "social_content": 1,
    "offer_optimizer": 2,
}


class CreditSystem:
    """
    Manages credit system for agent executions.
    """
    
    @staticmethod
    def get_monthly_credit_allocation(tier: str) -> int:
        """
        Get monthly credit allocation for tier.
        
        Args:
            tier: Subscription tier (free/pro/enterprise)
            
        Returns:
            Number of credits per month
        """
        return CREDIT_LIMITS.get(tier, 20)
    
    @staticmethod
    def get_agent_cost(agent_type: str) -> int:
        """
        Get execution cost for agent.
        
        Args:
            agent_type: Type identifier (e.g., "lead_generator")
            
        Returns:
            Cost in credits
        """
        return AGENT_COSTS.get(agent_type, 1)
    
    @staticmethod
    def get_used_credits_this_month(user: User, db: Session) -> int:
        """
        Get total credits used by user this month.
        
        Args:
            user: User object
            db: Database session
            
        Returns:
            Total credits used
        """
        month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        # Query credit transactions for this month with type="usage"
        used = db.query(CreditTransaction).filter(
            CreditTransaction.user_id == user.id,
            CreditTransaction.type == "usage",
            CreditTransaction.created_at >= month_start
        ).all()
        
        total_used = sum(abs(t.amount) for t in used if t.amount < 0)
        return int(total_used)
    
    @staticmethod
    def get_available_credits_this_month(user: User, db: Session) -> int:
        """
        Get available credits remaining for user this month.
        
        Args:
            user: User object
            db: Database session
            
        Returns:
            Credits remaining (0 if none)
        """
        tier = user.subscription_tier or "free"
        allocated = CreditSystem.get_monthly_credit_allocation(tier)
        
        if tier == "enterprise":
            return int(float("inf"))
        
        used = CreditSystem.get_used_credits_this_month(user, db)
        remaining = allocated - used
        
        return max(0, remaining)
    
    @staticmethod
    def deduct_credits(
        user: User,
        db: Session,
        amount: int,
        agent_type: str,
        execution_id: str
    ) -> bool:
        """
        Deduct credits from user's monthly allocation.
        
        IMPORTANT: Call ONLY AFTER execution succeeds.
        
        Args:
            user: User object
            db: Database session
            amount: Number of credits to deduct
            agent_type: Type of agent that was executed
            execution_id: ID of execution for reference
            
        Returns:
            True if deduction successful, False if insufficient credits
        """
        # Check available credits
        available = CreditSystem.get_available_credits_this_month(user, db)
        
        if amount > available:
            logger.warning(
                f"Insufficient credits for user {user.id}: "
                f"requested {amount}, available {available}"
            )
            return False
        
        # Record credit transaction
        transaction = CreditTransaction(
            user_id=user.id,
            amount=-amount,  # Negative for deduction
            type="usage",
            description=f"Executed {agent_type} agent",
            agent_type=agent_type,
            reference_id=execution_id
        )
        
        db.add(transaction)
        
        try:
            db.commit()
            logger.info(
                f"Deducted {amount} credits from user {user.id} "
                f"for {agent_type} execution"
            )
            return True
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to deduct credits: {e}")
            return False
    
    @staticmethod
    def grant_credits(
        user: User,
        db: Session,
        amount: int,
        reason: str = "manual_grant"
    ) -> bool:
        """
        Add credits to user's account.
        
        Args:
            user: User object
            db: Database session
            amount: Number of credits to add
            reason: Reason for granting credits
            
        Returns:
            True if successful
        """
        transaction = CreditTransaction(
            user_id=user.id,
            amount=amount,  # Positive for grants
            type="purchase" if "purchase" in reason else "monthly_grant",
            description=reason,
        )
        
        db.add(transaction)
        
        try:
            db.commit()
            logger.info(f"Granted {amount} credits to user {user.id}: {reason}")
            return True
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to grant credits: {e}")
            return False
    
    @staticmethod
    def monthly_reset(db: Session) -> int:
        """
        Reset monthly credit allocations for all users.
        
        Should be called as a scheduled job at start of each month.
        
        Args:
            db: Database session
            
        Returns:
            Number of users updated
        """
        from models.user import User
        
        users = db.query(User).filter(User.is_active == True).all()
        count = 0
        
        for user in users:
            tier = user.subscription_tier or "free"
            allocated = CreditSystem.get_monthly_credit_allocation(tier)
            
            if tier != "enterprise" and allocated > 0:
                transaction = CreditTransaction(
                    user_id=user.id,
                    amount=allocated,
                    type="monthly_grant",
                    description=f"{tier.capitalize()} tier monthly allocation"
                )
                db.add(transaction)
                count += 1
        
        try:
            db.commit()
            logger.info(f"Monthly credit reset: {count} users")
            return count
        except Exception as e:
            db.rollback()
            logger.error(f"Monthly reset failed: {e}")
            return 0
    
    @staticmethod
    def refund_credits(
        user: User,
        db: Session,
        amount: int,
        reason: str,
        reference_id: str = None
    ) -> bool:
        """
        Refund credits to user.
        
        Args:
            user: User object
            db: Database session
            amount: Number of credits to refund
            reason: Reason for refund
            reference_id: Original execution ID
            
        Returns:
            True if successful
        """
        transaction = CreditTransaction(
            user_id=user.id,
            amount=amount,
            type="refund",
            description=reason,
            reference_id=reference_id
        )
        
        db.add(transaction)
        
        try:
            db.commit()
            logger.info(f"Refunded {amount} credits to user {user.id}: {reason}")
            return True
        except Exception as e:
            db.rollback()
            logger.error(f"Refund failed: {e}")
            return False
