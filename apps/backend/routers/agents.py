from fastapi import APIRouter, Depends, HTTPException, status, Request
import asyncio
from sqlalchemy.orm import Session
from sqlalchemy import or_
from database_production import get_db
from models import Agent, User, Execution, AgentVersion
from models.monetization import Wallet
from schemas import AgentCreate, AgentUpdate, Agent as AgentSchema
from typing import List, Dict, Any, Optional
from services.agent_service import AgentService
from services.agent_runner import run_agent as execute_agent
from services.execution_policy import enforce_execution_policy, record_successful_execution
from security import get_current_user
from services.audit_service import audit_service
from services.encryption import encryption_service
from utils.agent_serialization import normalize_agent, serialize_agent
from services.usage_billing import record_usage
from celery_app import celery_app
from services.queue_protection import enqueue_task
from config_production import settings
from services.redis_service import get_rate_limiter
from services.abuse_filter import abuse_filter
from services.demo_agent import ensure_demo_agent
from services.execution_policy import _is_truthy
from services.wallet_service import serialize_amount
from utils.prometheus_metrics import record_request_timeout
import json
from pydantic import BaseModel
import logging
from datetime import datetime
import time
from routers.billing import check_subscription_limit

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agents", tags=["agents"])

_PUBLIC_RATE_LIMIT = settings.PUBLIC_EMBED_RATE_LIMIT
_PUBLIC_RATE_WINDOW_SECONDS = settings.PUBLIC_EMBED_RATE_WINDOW_SECONDS
_public_rate_state: Dict[str, tuple[int, float]] = {}
_redis_rate_limiter = get_rate_limiter()


def _map_agent_run_exception(exc: Exception) -> HTTPException:
    if isinstance(exc, HTTPException):
        return exc

    message = str(exc).lower()
    if "queue is full" in message or "retry shortly" in message:
        return HTTPException(status_code=429, detail="AI execution queue is full. Please retry shortly.")
    if "timed out" in message or "timeout" in message:
        return HTTPException(status_code=504, detail="Agent execution timed out. Please retry.")
    return HTTPException(status_code=500, detail="Agent execution failed. Please retry.")


def _check_public_rate_limit(ip: str) -> bool:
    now = time.time()
    if not ip:
        return True
    if _redis_rate_limiter and getattr(_redis_rate_limiter, "client", None):
        result = _redis_rate_limiter.is_allowed(
            f"public_agent:{ip}",
            limit=_PUBLIC_RATE_LIMIT,
            window=_PUBLIC_RATE_WINDOW_SECONDS
        )
        return bool(result.get("allowed", True))
    record = _public_rate_state.get(ip)
    if not record or (now - record[1]) > _PUBLIC_RATE_WINDOW_SECONDS:
        _public_rate_state[ip] = (1, now)
        return True
    count, start_ts = record
    if count >= _PUBLIC_RATE_LIMIT:
        return False
    _public_rate_state[ip] = (count + 1, start_ts)
    if len(_public_rate_state) > 5000:
        cutoff = now - _PUBLIC_RATE_WINDOW_SECONDS * 2
        for key, value in list(_public_rate_state.items()):
            if value[1] < cutoff:
                _public_rate_state.pop(key, None)
    return True

# Keep /test above parameterized routes to avoid shadowing by /{agent_id}
@router.get("/test")
def test():
    return {"status": "router working"}

# --- Versioning Schemas ---
class AgentVersionSchema(BaseModel):
    id: int
    version: str
    created_at: datetime
    description: Optional[str] = None
    class Config:
        from_attributes = True

class VersionCreate(BaseModel):
    version: str
    description: Optional[str] = None


# Helper to process agent for response (decrypt config)
def process_agent_response(agent: Agent):
    return normalize_agent(agent)


def resolve_agent_for_user(
    db: Session,
    agent_id: int,
    current_user: Optional[User],
    allow_system: bool = True,
    require_owner: bool = False,
    create_if_missing: bool = True
) -> tuple[Optional[Agent], bool]:
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if agent and (not require_owner or agent.owner_id == current_user.id):
        return agent, False

    query = db.query(Agent)
    if current_user:
        if require_owner:
            query = query.filter(Agent.owner_id == current_user.id)
        elif allow_system:
            query = query.filter(
                or_(Agent.owner_id == current_user.id, Agent.owner_id == None)
            )
        else:
            query = query.filter(Agent.owner_id == current_user.id)

    fallback = query.order_by(Agent.id).first()
    if fallback:
        return fallback, True

    if create_if_missing and current_user:
        default_config = encryption_service.encrypt_data(
            {"system_prompt": "You are a helpful assistant."}
        )
        new_agent = Agent(
            name="Auto Agent",
            description="Auto-created fallback agent",
            config=default_config,
            owner_id=current_user.id,
            is_published=False
        )
        db.add(new_agent)
        db.commit()
        db.refresh(new_agent)
        return new_agent, True

    if create_if_missing and not current_user:
        default_config = encryption_service.encrypt_data(
            {"system_prompt": "You are a helpful assistant."}
        )
        new_agent = Agent(
            name="Auto Agent",
            description="Auto-created fallback agent",
            config=default_config,
            owner_id=None,
            is_published=True
        )
        db.add(new_agent)
        db.commit()
        db.refresh(new_agent)
        return new_agent, True

    return None, False

class AgentRunRequest(BaseModel):
    input_data: Optional[str] = None

class PublicAgentRunRequest(BaseModel):
    input_data: Optional[str] = None

@router.post("/", response_model=AgentSchema)
def create_agent(agent: AgentCreate, request: Request, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if settings.EMAIL_VERIFICATION_REQUIRED and not _is_truthy(current_user.is_email_verified):
        raise HTTPException(status_code=403, detail="Please verify your email before creating agents.")
    # Check Subscription Limit
    current_count = db.query(Agent).filter(Agent.owner_id == current_user.id).count()
    check_subscription_limit(db, current_user.id, "agents", current_count)
    
    encrypted_config = None
    if agent.config:
        encrypted_config = encryption_service.encrypt_data(agent.config)
        
    db_agent = Agent(name=agent.name, description=agent.description, config=encrypted_config, owner_id=current_user.id)
    db.add(db_agent)
    db.commit()
    db.refresh(db_agent)
    
    # Audit Log
    audit_service.log_action(
        db, current_user.id, "create_agent", "agent", str(db_agent.id), 
        details={"name": agent.name}, ip_address=request.client.host
    )
    
    return serialize_agent(db_agent)

@router.get("/", response_model=List[AgentSchema])
def list_agents(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # Return system agents (owner_id is NULL) and user's own agents
    try:
        agents = db.query(Agent).filter(
            or_(
                Agent.owner_id == None,
                Agent.owner_id == current_user.id
            )
        ).all()
        return [serialize_agent(a) for a in agents if a is not None]
    except Exception as e:
        logger.error(f"Failed to list agents for user {current_user.id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={"success": False, "error": "Failed to list agents", "code": 500}
        )

@router.get("/{agent_id}", response_model=AgentSchema)
def get_agent(agent_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        agent, _ = resolve_agent_for_user(db, agent_id, current_user, allow_system=True)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    # Check permission: System agent or Owner or Admin
    if agent.owner_id and agent.owner_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized to view this agent")
        
    return serialize_agent(agent)


@router.get("/public/{agent_id}")
def get_public_agent(agent_id: int, db: Session = Depends(get_db)):
    agent = db.query(Agent).filter(
        Agent.id == agent_id,
        Agent.is_published == True
    ).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    from models import AgentReview
    reviews = db.query(AgentReview).filter(AgentReview.agent_id == agent.id).all()
    rating = 0.0
    if reviews:
        rating = sum(r.rating for r in reviews) / len(reviews)

    return {
        "id": agent.id,
        "name": agent.name,
        "description": agent.description,
        "category": agent.category,
        "tags": agent.tags,
        "rating": round(rating, 2),
        "is_published": agent.is_published
    }


@router.get("/public/demo")
def get_demo_agent(db: Session = Depends(get_db)):
    agent = ensure_demo_agent(db)
    return {
        "id": agent.id,
        "name": agent.name,
        "description": agent.description,
        "category": agent.category,
        "tags": agent.tags,
        "is_published": agent.is_published
    }


@router.post("/public/{agent_id}/run")
async def run_public_agent(
    agent_id: int,
    request: Request,
    payload: Optional[PublicAgentRunRequest] = None,
    db: Session = Depends(get_db)
):
    client_ip = request.client.host if request and request.client else ""
    if not _check_public_rate_limit(client_ip):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    agent = db.query(Agent).filter(
        Agent.id == agent_id,
        Agent.is_published == True
    ).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    input_data = payload.input_data if payload else None
    decision = abuse_filter.check(input_data)
    if not decision["allowed"]:
        logger.warning(
            "Blocked public agent prompt",
            extra={"agent_id": agent_id, "reason": decision.get("reason"), "matches": decision.get("matches")}
        )
        audit_service.log_action(
            db, None, "blocked_prompt", "public_agent", str(agent_id),
            details={
                "reason": decision.get("reason"),
                "matches": decision.get("matches"),
                "preview": decision.get("preview")
            },
            ip_address=client_ip
        )
        raise HTTPException(status_code=400, detail="Prompt blocked by safety filter.")
    execution = await execute_agent(db, agent.id, input_data=input_data, user_id=None)
    return {
        "status": execution.status,
        "result": execution.result,
        "execution_id": execution.id,
        "prompt_version_id": execution.prompt_version_id
    }

@router.put("/{agent_id}", response_model=AgentSchema)
def update_agent(
    agent_id: int,
    agent_update: AgentUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update an existing agent"""
    try:
        agent = db.query(Agent).filter(Agent.id == agent_id).first()
        if not agent:
            agent, _ = resolve_agent_for_user(
                db,
                agent_id,
                current_user,
                allow_system=False,
                require_owner=True
            )
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")

        # Check permission: Owner or Admin
        if agent.owner_id != current_user.id and current_user.role != "admin":
            raise HTTPException(status_code=403, detail="Not authorized to update this agent")

        # Encrypt config if provided
        encrypted_config = None
        if agent_update.config is not None:
            encrypted_config = encryption_service.encrypt_data(agent_update.config)

        # Update agent using service
        updated_agent = AgentService.update_agent(
            db=db,
            agent=agent,
            agent_data=agent_update,
            encrypted_config=encrypted_config
        )

        # Audit Log
        audit_service.log_action(
            db, current_user.id, "update_agent", "agent", str(agent_id),
            details={"updated_fields": list(agent_update.dict(exclude_unset=True).keys())},
            ip_address=request.client.host if request.client else None
        )

        return serialize_agent(updated_agent)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update agent {agent_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={"success": False, "error": "Failed to update agent", "details": str(e), "code": 500}
        )

@router.delete("/{agent_id}")
def delete_agent(
    agent_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete an agent"""
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Check permission: Owner or Admin
    if agent.owner_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized to delete this agent")

    # Cannot delete system agents (owner_id is NULL)
    if agent.owner_id is None:
        raise HTTPException(status_code=403, detail="Cannot delete system agents")

    # Delete agent using service
    AgentService.delete_agent(db=db, agent=agent)

    # Audit Log
    audit_service.log_action(
        db, current_user.id, "delete_agent", "agent", str(agent_id),
        details={"name": agent.name},
        ip_address=request.client.host
    )

    return {"message": "Agent deleted successfully"}

@router.post("/{agent_id}/run")
async def run_agent(
    agent_id: int,
    request: Request,
    run_req: Optional[AgentRunRequest] = None,
    async_execution: bool = True,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Check if agent exists
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
        
    # Check permission: System agent or Owner or Admin
    if agent.owner_id and agent.owner_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized to run this agent")

    # ✅ UNIFIED EXECUTION GATE: Checks email verification, subscription, execution limit, wallet
    enforce_execution_policy(current_user, db)

    input_data = run_req.input_data if run_req else None
    decision = abuse_filter.check(input_data)
    if not decision["allowed"]:
        logger.warning(
            "Blocked agent prompt",
            extra={
                "agent_id": agent.id,
                "user_id": current_user.id,
                "reason": decision.get("reason"),
                "matches": decision.get("matches")
            }
        )
        audit_service.log_action(
            db, current_user.id, "blocked_prompt", "agent", str(agent.id),
            details={
                "reason": decision.get("reason"),
                "matches": decision.get("matches"),
                "preview": decision.get("preview")
            },
            ip_address=request.client.host if request.client else None
        )
        raise HTTPException(status_code=400, detail="Prompt blocked by safety filter.")
    wallet = None
    try:
        if settings.ENABLE_ASYNC_EXECUTION and async_execution:
            task = enqueue_task(
                "tasks.agent_tasks.execute_agent",
                args=[{"agent_id": agent.id, "input_data": input_data, "user_id": current_user.id}],
                queue="agent_executions"
            )
            audit_service.log_action(
                db, current_user.id, "run_agent_queued", "agent", str(agent.id),
                details={"input": input_data, "task_id": task.id},
                ip_address=request.client.host if request.client else None
            )
            return {"status": "queued", "task_id": task.id}

        # ✅ EXECUTE: Run the agent (sync)
        execution = await asyncio.wait_for(
            execute_agent(db, agent.id, input_data=input_data, user_id=current_user.id),
            timeout=settings.effective_request_timeout_seconds
        )
        
        # ✅ RECORD: Post-execution tracking (ONLY if success)
        record_successful_execution(current_user, db, tokens_used=execution.token_usage if execution.token_usage else 0)
        
        # Usage billing + wallet deduction
        cost = 1.0
        record_usage(
            db=db,
            user_id=current_user.id,
            execution_type="agent_run",
            cost=cost,
            tokens_used=execution.token_usage if execution.token_usage else 0,
            compute_time_ms=execution.execution_time_ms if getattr(execution, "execution_time_ms", None) else 0,
            agent_id=agent.id
        )
        wallet = db.query(Wallet).filter(Wallet.user_id == current_user.id).first()
        
        # Audit Log
        audit_service.log_action(
            db, current_user.id, "run_agent", "agent", str(agent.id),
            details={"input": input_data, "execution_id": execution.id, "cost": cost}, 
            ip_address=request.client.host
        )
        
        return {
            "status": execution.status,
            "result": execution.result,
            "execution_id": execution.id,
            "prompt_version_id": execution.prompt_version_id,
            "agent_run_id": getattr(execution, "agent_run_id", None),
            "cost": cost,
            "remaining_credits": serialize_amount(wallet.balance) if wallet else 0
        }
    except asyncio.TimeoutError:
        record_request_timeout("/agents/{agent_id}/run")
        logger.info(
            "Request timeout reached, returning 504 for agent %s user %s after %ss",
            agent.id,
            current_user.id,
            settings.effective_request_timeout_seconds,
        )
        audit_service.log_action(
            db, current_user.id, "run_agent_timeout", "agent", str(agent.id),
            details={"input": input_data, "timeout_seconds": settings.effective_request_timeout_seconds},
            ip_address=request.client.host if request.client else None
        )
        raise HTTPException(status_code=504, detail="Agent execution timed out. Please retry.")
    except HTTPException:
        # Re-raise HTTP exceptions (from enforcement gate, etc.)
        raise
    except Exception as e:
        mapped_error = _map_agent_run_exception(e)
        if mapped_error.status_code in (429, 504):
            logger.info("Agent run ended with expected %s: %s", mapped_error.status_code, mapped_error.detail)
        else:
            logger.error(f"Execution failed: {e}", exc_info=True)
        audit_service.log_action(
            db, current_user.id, "run_agent_error", "agent", str(agent.id),
            details={"error": str(e), "status_code": mapped_error.status_code},
            ip_address=request.client.host if request.client else None
        )
        raise mapped_error

@router.post("/{agent_id}/clone", response_model=AgentSchema)
def clone_agent(agent_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    original = db.query(Agent).filter(Agent.id == agent_id).first()
    if not original:
        original, _ = resolve_agent_for_user(db, agent_id, current_user, allow_system=True)
    if not original:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    # Decrypt original config if present, then encrypt again for new agent
    # Actually we can just copy the encrypted string directly if the key is the same.
    # But to be safe and consistent (and in case we rotate keys), let's decrypt then encrypt.
    original_config = None
    if original.config:
        decrypted = encryption_service.decrypt_data(original.config)
        original_config = encryption_service.encrypt_data(decrypted)

    new_agent = Agent(
        name=f"Copy of {original.name}",
        description=original.description,
        config=original_config,
        owner_id=current_user.id
    )
    db.add(new_agent)
    db.commit()
    db.refresh(new_agent)
    
    # Audit Log for clone
    audit_service.log_action(
        db, current_user.id, "clone_agent", "agent", str(new_agent.id), 
        details={"original_id": agent_id}, ip_address=None
    )
    
    return serialize_agent(new_agent)

# --- Versioning ---

@router.post("/{agent_id}/versions", response_model=AgentVersionSchema)
def create_version(
    agent_id: int,
    version_data: VersionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        agent, _ = resolve_agent_for_user(
            db,
            agent_id,
            current_user,
            allow_system=False,
            require_owner=True
        )
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    if agent.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
        
    # Decrypt current config to store as snapshot
    config_snapshot = {}
    if agent.config:
        try:
            config_snapshot = encryption_service.decrypt_data(agent.config)
        except:
            config_snapshot = {}
            
    new_version = AgentVersion(
        agent_id=agent_id,
        version=version_data.version,
        config=config_snapshot, 
        description=version_data.description
    )
    db.add(new_version)
    
    # Update current version string
    agent.version = version_data.version
    
    db.commit()
    db.refresh(new_version)
    return new_version

@router.get("/{agent_id}/versions", response_model=List[AgentVersionSchema])
def list_versions(
    agent_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        agent, _ = resolve_agent_for_user(
            db,
            agent_id,
            current_user,
            allow_system=False,
            require_owner=True
        )
    if not agent:
        return []

    if agent.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    return db.query(AgentVersion).filter(
        AgentVersion.agent_id == agent.id
    ).order_by(AgentVersion.created_at.desc()).all()

@router.post("/{agent_id}/rollback/{version_id}", response_model=AgentSchema)
def rollback_version(
    agent_id: int,
    version_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        agent, _ = resolve_agent_for_user(
            db,
            agent_id,
            current_user,
            allow_system=False,
            require_owner=True
        )
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    if agent.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    version = db.query(AgentVersion).filter(
        AgentVersion.id == version_id,
        AgentVersion.agent_id == agent.id
    ).first()
    if not version:
        version = db.query(AgentVersion).filter(
            AgentVersion.agent_id == agent.id
        ).order_by(AgentVersion.created_at.desc()).first()
    if not version:
        return serialize_agent(agent)
        
    # Restore config
    if version.config:
        agent.config = encryption_service.encrypt_data(version.config)
    else:
        agent.config = None
        
    agent.version = version.version
    db.commit()
    db.refresh(agent)
    return serialize_agent(agent)
