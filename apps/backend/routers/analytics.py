from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database_production import get_db
from security import get_current_user
from services.analytics_service import AnalyticsService
from models import FounderRun

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/agents/{agent_id}/success-rate")
def agent_success_rate(
    agent_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    return AnalyticsService.agent_success_rate(db, agent_id)


@router.get("/agents/{agent_id}/tool-performance")
def agent_tool_performance(
    agent_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    return {
        "agent_id": agent_id,
        "tools": AnalyticsService.tool_performance(db, agent_id)
    }


@router.get("/agents/{agent_id}/prompt-performance")
def agent_prompt_performance(
    agent_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    return {
        "agent_id": agent_id,
        "prompts": AnalyticsService.prompt_performance(db, agent_id)
    }


@router.get("/summary")
def analytics_summary(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    return AnalyticsService.task_completion(db)


@router.get("/founder-runs")
def founder_runs(
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    runs = (
        db.query(FounderRun)
        .order_by(FounderRun.created_at.desc())
        .limit(limit)
        .all()
    )
    return {
        "count": len(runs),
        "runs": [
            {
                "id": run.id,
                "run_type": run.run_type,
                "status": run.status,
                "summary": run.summary,
                "trend_snapshot": run.trend_snapshot,
                "created_at": run.created_at,
                "error": run.error
            }
            for run in runs
        ]
    }


@router.get("/founder-runs/{run_id}")
def founder_run_detail(
    run_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    run = db.query(FounderRun).filter(FounderRun.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Founder run not found")
    return {
        "id": run.id,
        "run_type": run.run_type,
        "status": run.status,
        "trend_snapshot": run.trend_snapshot,
        "automation_ideas": run.automation_ideas,
        "agents_created": run.agents_created,
        "workflows_created": run.workflows_created,
        "templates_published": run.templates_published,
        "listings_published": run.listings_published,
        "summary": run.summary,
        "error": run.error,
        "created_at": run.created_at
    }
