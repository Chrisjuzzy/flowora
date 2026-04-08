from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database_production import get_db
from services.trending_service import TrendingService

router = APIRouter(prefix="/trending", tags=["trending"])


@router.get("/agents")
def trending_agents(limit: int = 10, db: Session = Depends(get_db)):
    return {"agents": TrendingService.top_agents(db, limit=limit)}


@router.get("/workflows")
def trending_workflows(limit: int = 10, db: Session = Depends(get_db)):
    return {"workflows": TrendingService.top_workflows(db, limit=limit)}


@router.get("/plugins")
def trending_plugins(limit: int = 10, db: Session = Depends(get_db)):
    return {"plugins": TrendingService.top_plugins(db, limit=limit)}


@router.get("/summary")
def trending_summary(limit: int = 10, db: Session = Depends(get_db)):
    return {
        "agents": TrendingService.top_agents(db, limit=limit),
        "workflows": TrendingService.top_workflows(db, limit=limit),
        "plugins": TrendingService.top_plugins(db, limit=limit)
    }
