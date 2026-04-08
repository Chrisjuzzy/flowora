"""
=====================================
REVENUE TRACKING ROUTER
=====================================

User endpoints for reporting and tracking revenue generated via the platform.

Public endpoints that allow users to report revenue their agents/workflows generated.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from sqlalchemy import func
from database_production import get_db
from models.user import User
from models.monetization import UserRevenueTracking
from security import get_current_user
from pydantic import BaseModel
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/revenue", tags=["revenue"])


class RevenueReportCreate(BaseModel):
    """Schema for creating revenue report."""
    reported_revenue: float
    source_agent: str = None  # Agent type that generated the revenue
    description: str = None  # How revenue was generated


class RevenueReport(RevenueReportCreate):
    """Revenueport schema with metadata."""
    id: int
    user_id: int
    verified: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


class RevenueSummary(BaseModel):
    """User's revenue summary."""
    total_reported_revenue: float
    verified_revenue: float
    unverified_revenue: float
    report_count: int
    by_agent: dict  # Agent type -> revenue


@router.post("/report", response_model=RevenueReport)
def report_revenue(
    report: RevenueReportCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    request: Request = None
):
    """
    Report revenue generated using the platform.
    
    Users can report revenue their agents/workflows generated.
    This helps build credibility and provides social proof.
    Reports can be verified by admins for marketing purposes.
    
    Args:
        report: Revenue report details
        
    Returns:
        Created revenue report
        
    Raises:
        HTTPException(400): If validation fails
    """
    if report.reported_revenue <= 0:
        raise HTTPException(
            status_code=400,
            detail="Reported revenue must be positive"
        )
    
    if report.reported_revenue > 10_000_000:  # Sanity check (10M max)
        raise HTTPException(
            status_code=400,
            detail="Reported revenue seems unusually high. Check your input."
        )
    
    # Create revenue report
    revenue_report = UserRevenueTracking(
        user_id=current_user.id,
        reported_revenue=report.reported_revenue,
        source_agent=report.source_agent,
        description=report.description,
        verified=False  # Requires admin verification
    )
    
    db.add(revenue_report)
    
    try:
        db.commit()
        db.refresh(revenue_report)
        
        logger.info(
            f"User {current_user.id} reported ${report.reported_revenue} revenue "
            f"from agent {report.source_agent}"
        )
        
        return revenue_report
    
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to record revenue report: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to record revenue report"
        )


@router.get("/summary", response_model=RevenueSummary)
def get_revenue_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get user's revenue summary.
    
    Returns total reported revenue, verified vs unverified breakdown,
    and breakdown by agent type.
    
    Args:
        None
        
    Returns:
        User's revenue summary
    """
    # Get all reports for user
    reports = db.query(UserRevenueTracking).filter(
        UserRevenueTracking.user_id == current_user.id
    ).all()
    
    total_revenue = sum(r.reported_revenue for r in reports)
    verified_revenue = sum(r.reported_revenue for r in reports if r.verified)
    unverified_revenue = total_revenue - verified_revenue
    
    # Breakdown by agent
    by_agent = {}
    for report in reports:
        agent = report.source_agent or "unspecified"
        if agent not in by_agent:
            by_agent[agent] = 0
        by_agent[agent] += report.reported_revenue
    
    return RevenueSummary(
        total_reported_revenue=total_revenue,
        verified_revenue=verified_revenue,
        unverified_revenue=unverified_revenue,
        report_count=len(reports),
        by_agent=by_agent
    )


@router.get("/reports")
def get_revenue_reports(
    limit: int = 50,
    verified_only: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get user's revenue reports.
    
    Args:
        limit: Maximum reports to return
        verified_only: Only return verified reports
        
    Returns:
        List of revenue reports
    """
    query = db.query(UserRevenueTracking).filter(
        UserRevenueTracking.user_id == current_user.id
    )
    
    if verified_only:
        query = query.filter(UserRevenueTracking.verified == True)
    
    reports = query.order_by(
        UserRevenueTracking.created_at.desc()
    ).limit(limit).all()
    
    return reports


@router.get("/leaderboard")
def get_revenue_leaderboard(
    limit: int = 10,
    db: Session = Depends(get_db)
):
    """
    Get top revenue reporters.
    
    Public leaderboard showing users who generated the most revenue.
    Anonymous IDs used for privacy.
    
    Args:
        limit: Top N users to return
        
    Returns:
        List of top revenue reporters
    """
    # Query top users by verified revenue
    top_users = db.query(
        UserRevenueTracking.user_id,
        func.sum(UserRevenueTracking.reported_revenue).label("total_revenue"),
        func.count(UserRevenueTracking.id).label("report_count")
    ).filter(
        UserRevenueTracking.verified == True
    ).group_by(
        UserRevenueTracking.user_id
    ).order_by(
        func.sum(UserRevenueTracking.reported_revenue).desc()
    ).limit(limit).all()
    
    return [
        {
            "rank": idx + 1,
            "user_id": row[0],
            "total_revenue": row[1],
            "report_count": row[2]
        }
        for idx, row in enumerate(top_users)
    ]


@router.delete("/reports/{report_id}")
def delete_revenue_report(
    report_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete a revenue report.
    
    Users can only delete their own unverified reports.
    
    Args:
        report_id: Report to delete
        
    Returns:
        Confirmation message
        
    Raises:
        HTTPException(404): If not found
        HTTPException(403): If user doesn't own report or it's verified
    """
    report = db.query(UserRevenueTracking).filter(
        UserRevenueTracking.id == report_id
    ).first()
    
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    
    if report.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Can only delete your own reports")
    
    if report.verified:
        raise HTTPException(status_code=403, detail="Cannot delete verified reports")
    
    db.delete(report)
    
    try:
        db.commit()
        logger.info(f"User {current_user.id} deleted revenue report {report_id}")
        return {"status": "success", "message": "Report deleted"}
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to delete report: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete report")
