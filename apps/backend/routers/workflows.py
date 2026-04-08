import asyncio

from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy.orm import Session
from typing import List, Optional, Any, Dict
import schemas
import models
from database_production import get_db
from security import get_current_user
from services.workflow_runner import run_workflow as execute_workflow
from services.execution_policy import enforce_execution_policy, record_successful_execution
from celery_app import celery_app
from services.queue_protection import enqueue_task
from config_production import settings
from services.abuse_filter import abuse_filter
from services.audit_service import audit_service
import logging

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/workflows",
    tags=["workflows"],
)


def _map_workflow_exception(exc: Exception) -> HTTPException:
    if isinstance(exc, HTTPException):
        return exc

    message = str(exc).lower()
    if "queue is full" in message or "retry shortly" in message:
        return HTTPException(status_code=429, detail="Workflow execution queue is full. Please retry shortly.")
    if "timed out" in message or "timeout" in message:
        return HTTPException(status_code=504, detail="Workflow execution timed out. Please retry.")
    if isinstance(exc, ValueError):
        return HTTPException(status_code=400, detail=str(exc))
    return HTTPException(status_code=500, detail="Workflow execution failed. Please retry.")

@router.get("/", response_model=List[schemas.Workflow])
def list_workflows(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    return db.query(models.Workflow).filter(models.Workflow.owner_id == current_user.id).all()

@router.get("/public/{workflow_id}")
def get_public_workflow(workflow_id: int, db: Session = Depends(get_db)):
    workflow = db.query(models.Workflow).filter(
        models.Workflow.id == workflow_id,
        models.Workflow.is_public == True
    ).first()
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return {
        "id": workflow.id,
        "name": workflow.name,
        "description": workflow.description,
        "config_json": workflow.config_json,
        "clone_count": workflow.clone_count,
        "install_count": workflow.install_count
    }

@router.post("/", response_model=schemas.Workflow)
def create_workflow(workflow: schemas.WorkflowCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    db_workflow = models.Workflow(
        name=workflow.name,
        description=getattr(workflow, "description", None),
        config_json=workflow.config_json,
        owner_id=current_user.id,
        is_public=getattr(workflow, "is_public", False)
    )
    db.add(db_workflow)
    db.commit()
    db.refresh(db_workflow)
    return db_workflow

@router.get("/{workflow_id}", response_model=schemas.Workflow)
def get_workflow(workflow_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    workflow = db.query(models.Workflow).filter(models.Workflow.id == workflow_id).first()
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    if workflow.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this workflow")
    return workflow


@router.post("/{workflow_id}/clone", response_model=schemas.Workflow)
def clone_workflow(
    workflow_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    workflow = db.query(models.Workflow).filter(models.Workflow.id == workflow_id).first()
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    if workflow.owner_id != current_user.id and not workflow.is_public:
        raise HTTPException(status_code=403, detail="Not authorized to clone this workflow")

    new_workflow = models.Workflow(
        name=f"Copy of {workflow.name}",
        description=workflow.description,
        config_json=workflow.config_json,
        owner_id=current_user.id,
        is_public=False
    )
    db.add(new_workflow)
    workflow.clone_count = (workflow.clone_count or 0) + 1
    db.commit()
    db.refresh(new_workflow)
    return new_workflow


@router.post("/{workflow_id}/install", response_model=schemas.Workflow)
def install_workflow(
    workflow_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    workflow = db.query(models.Workflow).filter(models.Workflow.id == workflow_id).first()
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    if workflow.owner_id != current_user.id and not workflow.is_public:
        raise HTTPException(status_code=403, detail="Not authorized to install this workflow")

    new_workflow = models.Workflow(
        name=f"{workflow.name} (Installed)",
        description=workflow.description,
        config_json=workflow.config_json,
        owner_id=current_user.id,
        is_public=False
    )
    db.add(new_workflow)
    workflow.install_count = (workflow.install_count or 0) + 1
    db.commit()
    db.refresh(new_workflow)
    return new_workflow


@router.post("/{workflow_id}/publish", response_model=schemas.Workflow)
def publish_workflow(
    workflow_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    workflow = db.query(models.Workflow).filter(models.Workflow.id == workflow_id).first()
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    if workflow.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to publish this workflow")
    workflow.is_public = True
    db.commit()
    db.refresh(workflow)
    return workflow

@router.post("/{workflow_id}/run")
async def run_workflow(
    workflow_id: int,
    input_data: Optional[str] = Body(None, embed=True),
    async_execution: bool = True,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    workflow = db.query(models.Workflow).filter(models.Workflow.id == workflow_id).first()
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    if workflow.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to run this workflow")
    
    # ✅ UNIFIED EXECUTION GATE: Checks email verification, subscription, execution limit, wallet
    enforce_execution_policy(current_user, db)

    decision = abuse_filter.check(input_data)
    if not decision["allowed"]:
        logger.warning(
            "Blocked workflow prompt",
            extra={
                "workflow_id": workflow_id,
                "user_id": current_user.id,
                "reason": decision.get("reason"),
                "matches": decision.get("matches")
            }
        )
        audit_service.log_action(
            db, current_user.id, "blocked_prompt", "workflow", str(workflow_id),
            details={
                "reason": decision.get("reason"),
                "matches": decision.get("matches"),
                "preview": decision.get("preview")
            },
            ip_address=None
        )
        raise HTTPException(status_code=400, detail="Prompt blocked by safety filter.")
    
    try:
        if settings.ENABLE_ASYNC_EXECUTION and async_execution:
            task = enqueue_task(
                "tasks.workflow_tasks.run_workflow",
                args=[{"workflow_id": workflow_id, "input_data": input_data, "user_id": current_user.id}],
                queue="workflows"
            )
            return {"status": "queued", "task_id": task.id}

        result = await asyncio.wait_for(
            execute_workflow(db, workflow_id, initial_input=input_data),
            timeout=settings.effective_request_timeout_seconds
        )

        record_successful_execution(current_user, db, tokens_used=0)
        return result
    except asyncio.TimeoutError:
        logger.info(
            "Workflow request timeout reached, returning 504 for workflow %s user %s after %ss",
            workflow_id,
            current_user.id,
            settings.effective_request_timeout_seconds,
        )
        raise HTTPException(status_code=504, detail="Workflow execution timed out. Please retry.")
    except Exception as e:
        mapped_error = _map_workflow_exception(e)
        if mapped_error.status_code in (429, 504):
            logger.info("Workflow run ended with expected %s: %s", mapped_error.status_code, mapped_error.detail)
        elif mapped_error.status_code == 400:
            logger.warning("Workflow run validation error: %s", e)
        else:
            logger.error("Workflow run failed: %s", e, exc_info=True)
        raise mapped_error
