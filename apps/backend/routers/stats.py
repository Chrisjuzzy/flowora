"""
=====================================
ADMIN STATISTICS ROUTER
=====================================

Admin-only endpoints for platform analytics and dashboard.

All endpoints require admin role.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from database import get_db
from models.user import User
from models.agents import Agent
from models.monetization import CreditTransaction, UserRevenueTracking
from security import get_current_user
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/stats", tags=["admin_stats"])


def verify_admin(current_user: User = Depends(get_current_user)) -> User:
    """Verify user is admin."""
    if getattr(current_user, 'role', None) != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    return current_user


@router.get("/platform")
def get_platform_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(verify_admin)
):
    """
    Get comprehensive platform statistics.
    
    Returns:
    - users: User counts by tier and status
    - executions: Execution metrics
    - credits: Credit system usage
    - revenue: Revenue simulation and tracking
    - agents: Agent usage statistics
    
    Admin only.
    """
    # User statistics
    total_users = db.query(func.count(User.id)).scalar() or 0
    active_users = db.query(func.count(User.id)).filter(
        User.subscription_status == "active"
    ).scalar() or 0
    verified_users = db.query(func.count(User.id)).filter(
        User.is_email_verified == True
    ).scalar() or 0
    
    # User breakdown by tier
    user_by_tier = {}
    for tier in ["free", "pro", "enterprise"]:
        count = db.query(func.count(User.id)).filter(
            User.subscription_tier == tier
        ).scalar() or 0
        user_by_tier[tier] = count
    
    # Execution statistics
    total_executions = db.query(func.sum(User.executions_this_month)).scalar() or 0
    avg_executions = total_executions / total_users if total_users > 0 else 0
    total_tokens = db.query(func.sum(User.tokens_used_this_month)).scalar() or 0
    
    # Credit statistics this month
    month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    total_credits_used = db.query(func.sum(
        func.abs(CreditTransaction.amount)
    )).filter(
        CreditTransaction.type == "usage",
        CreditTransaction.created_at >= month_start
    ).scalar() or 0
    
    total_credits_granted = db.query(func.sum(
        CreditTransaction.amount
    )).filter(
        CreditTransaction.type.in_(["monthly_grant", "purchase"]),
        CreditTransaction.created_at >= month_start
    ).scalar() or 0
    
    # Revenue statistics
    total_reported_revenue = db.query(func.sum(
        UserRevenueTracking.reported_revenue
    )).scalar() or 0
    
    verified_revenue = db.query(func.sum(
        UserRevenueTracking.reported_revenue
    )).filter(
        UserRevenueTracking.verified == True
    ).scalar() or 0
    
    # Agent usage by type
    agent_usage = {}
    agent_stats = db.query(
        CreditTransaction.agent_type,
        func.count(CreditTransaction.id).label("executions"),
        func.sum(func.abs(CreditTransaction.amount)).label("credits_used")
    ).filter(
        CreditTransaction.type == "usage"
    ).group_by(
        CreditTransaction.agent_type
    ).all()
    
    for stat in agent_stats:
        agent_usage[stat[0] or "unknown"] = {
            "executions": stat[1],
            "credits_used": int(stat[2]) if stat[2] else 0
        }
    
    # Estimated MRR
    pro_mrr = (user_by_tier.get("pro", 0) * 99)
    enterprise_mrr = (user_by_tier.get("enterprise", 0) * 999)
    total_estimated_mrr = pro_mrr + enterprise_mrr
    
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "users": {
            "total": total_users,
            "active": active_users,
            "email_verified": verified_users,
            "by_tier": user_by_tier
        },
        "executions": {
            "total": int(total_executions),
            "avg_per_user": round(avg_executions, 2),
            "total_tokens_processed": int(total_tokens)
        },
        "credits": {
            "total_used_month": int(total_credits_used),
            "total_granted_month": int(total_credits_granted),
            "net_deficit": int(total_credits_used - total_credits_granted)
        },
        "revenue": {
            "estimated_mrr": total_estimated_mrr,
            "user_reported_revenue": total_reported_revenue,
            "verified_revenue": verified_revenue,
            "unverified_revenue": total_reported_revenue - verified_revenue,
            "mrr_breakdown": {
                "pro": pro_mrr,
                "enterprise": enterprise_mrr
            }
        },
        "agents": agent_usage
    }


@router.get("/users")
def get_users_list(
    tier: str = None,
    status: str = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: User = Depends(verify_admin)
):
    """
    List users with optional filtering.
    
    Args:
        tier: Filter by tier (free/pro/enterprise)
        status: Filter by status (active/canceled/trialing)
        limit: Results per page
        offset: Pagination offset
        
    Returns:
        List of users with details
        
    Admin only.
    """
    query = db.query(User)
    
    if tier:
        query = query.filter(User.subscription_tier == tier)
    if status:
        query = query.filter(User.subscription_status == status)
    
    total = query.count()
    users = query.offset(offset).limit(limit).all()
    
    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "users": [
            {
                "id": u.id,
                "email": u.email,
                "tier": u.subscription_tier,
                "status": u.subscription_status,
                "verified": u.is_email_verified,
                "executions_month": u.executions_this_month,
                "tokens_month": u.tokens_used_this_month,
                "created": u.created_at.isoformat()
            }
            for u in users
        ]
    }


@router.get("/top-agents")
def get_top_agents(
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(verify_admin)
):
    """
    Get most popular agents by execution count.
    
    Args:
        limit: Number of top agents
        
    Returns:
        List of top agents with metrics
        
    Admin only.
    """
    top_agents = db.query(
        CreditTransaction.agent_type,
        func.count(CreditTransaction.id).label("times_executed"),
        func.sum(func.abs(CreditTransaction.amount)).label("total_credits_used")
    ).filter(
        CreditTransaction.type == "usage",
        CreditTransaction.agent_type != None
    ).group_by(
        CreditTransaction.agent_type
    ).order_by(
        func.count(CreditTransaction.id).desc()
    ).limit(limit).all()
    
    return [
        {
            "rank": idx + 1,
            "agent_type": stat[0],
            "times_executed": stat[1],
            "total_credits_used": int(stat[2]) if stat[2] else 0
        }
        for idx, stat in enumerate(top_agents)
    ]


@router.get("/revenue-reports")
def get_revenue_reports(
    verified: bool = None,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: User = Depends(verify_admin)
):
    """
    Get all revenue reports.
    
    Args:
        verified: Filter by verification status
        limit: Results per page
        offset: Pagination offset
        
    Returns:
        List of revenue reports
        
    Admin only.
    """
    query = db.query(UserRevenueTracking)
    
    if verified is not None:
        query = query.filter(UserRevenueTracking.verified == verified)
    
    total = query.count()
    reports = query.order_by(
        UserRevenueTracking.created_at.desc()
    ).offset(offset).limit(limit).all()
    
    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "reports": [
            {
                "id": r.id,
                "user_id": r.user_id,
                "revenue": r.reported_revenue,
                "agent": r.source_agent,
                "verified": r.verified,
                "created": r.created_at.isoformat()
            }
            for r in reports
        ]
    }


@router.post("/verify-revenue/{report_id}")
def verify_revenue_report(
    report_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(verify_admin)
):
    """
    Verify a revenue report for credibility.
    
    Args:
        report_id: Report ID to verify
        
    Returns:
        Updated report
        
    Admin only.
    """
    report = db.query(UserRevenueTracking).filter(
        UserRevenueTracking.id == report_id
    ).first()
    
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    
    report.verified = True
    
    try:
        db.commit()
        logger.info(f"Admin {current_user.id} verified revenue report {report_id}")
        return {
            "status": "success",
            "report_id": report_id,
            "verified": True
        }
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to verify report: {e}")
        raise HTTPException(status_code=500, detail="Failed to verify report")
