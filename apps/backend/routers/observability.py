from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database_production import get_db, check_db_connection
from utils.metrics import snapshot
from models import Execution, UsageLog
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/observability", tags=["observability"])


@router.get("/metrics")
def get_metrics():
    return snapshot()


@router.get("/system-health")
def system_health(db: Session = Depends(get_db)):
    db_ok = check_db_connection()
    return {
        "database": "ok" if db_ok else "error",
        "redis": "unknown",
        "queue": "unknown"
    }


@router.get("/execution-stats")
def execution_stats(db: Session = Depends(get_db)):
    total_executions = db.query(Execution).count()
    total_usage_logs = db.query(UsageLog).count()
    return {
        "executions": total_executions,
        "usage_logs": total_usage_logs
    }
