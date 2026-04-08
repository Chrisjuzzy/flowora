from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from database import get_db
from models import Agent, User, Execution, AgentVersion
from models.monetization import Wallet, Transaction
from schemas import AgentCreate, AgentUpdate, Agent as AgentSchema
from typing import List, Dict, Any, Optional
from services.agent_service import AgentService
from services.agent_runner import run_agent as execute_agent
from services.execution_policy import enforce_execution_policy, record_successful_execution
from security import get_current_user
from services.audit_service import audit_service
from services.encryption import encryption_service
from services.wallet_service import InsufficientBalanceError, debit_wallet, serialize_amount
from pydantic import BaseModel
import logging
from datetime import datetime
from routers.billing import check_subscription_limit

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agents", tags=["agents"])

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
    if agent.config:
        agent.config = encryption_service.decrypt_data(agent.config)
    return agent

class AgentRunRequest(BaseModel):
    input_data: Optional[str] = None

@router.post("/", response_model=AgentSchema)
@router.post("/create", response_model=AgentSchema)
def create_agent(agent: AgentCreate, request: Request, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # Check Subscription Limit
    current_count = db.query(Agent).filter(Agent.owner_id == current_user.id).count()
    check_subscription_limit(db, current_user.id, "agents", current_count)

    # Encrypt config if provided
    encrypted_config = None
    if agent.config:
        encrypted_config = encryption_service.encrypt_data(agent.config)

    # Create agent using service
    db_agent = AgentService.create_agent(
        db=db,
        agent_data=agent,
        owner_id=current_user.id,
        encrypted_config=encrypted_config
    )

    # Audit Log
    audit_service.log_action(
        db, current_user.id, "create_agent", "agent", str(db_agent.id),
        details={"name": agent.name, "role": agent.role, "skills": agent.skills}, 
        ip_address=request.client.host
    )

    return process_agent_response(db_agent)

from sqlalchemy import or_

@router.get("/", response_model=List[AgentSchema])
@router.get("/list", response_model=List[AgentSchema])
def list_agents(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # Return system agents (owner_id is NULL) and user's own agents
    agents = db.query(Agent).filter(
        or_(
            Agent.owner_id == None,
            Agent.owner_id == current_user.id
        )
    ).all()
    return [process_agent_response(a) for a in agents]

@router.get("/{agent_id}", response_model=AgentSchema)
def get_agent(agent_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Check permission: System agent or Owner or Admin
    if agent.owner_id and agent.owner_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized to view this agent")

    return process_agent_response(agent)

@router.put("/{agent_id}", response_model=AgentSchema)
@router.patch("/{agent_id}", response_model=AgentSchema)
def update_agent(
    agent_id: int,
    agent_update: AgentUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update an existing agent"""
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
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
        ip_address=request.client.host
    )

    return process_agent_response(updated_agent)

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
@router.post("/run/{agent_id}")
async def run_agent(agent_id: int, request: Request, run_req: Optional[AgentRunRequest] = None, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
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

    try:
        # ✅ EXECUTE: Run the agent
        execution = await execute_agent(db, agent_id, input_data=input_data, user_id=current_user.id)

        # ✅ RECORD: Post-execution tracking (ONLY if success)
        record_successful_execution(current_user, db, tokens_used=execution.token_usage if execution.token_usage else 0)

        # Deduct Credits (existing wallet system)
        cost = 1.0
        wallet = None
        try:
            wallet, _ = debit_wallet(
                db=db,
                user_id=current_user.id,
                amount=cost,
                transaction_type="execution_cost",
                description=f"Ran agent {agent.name}",
                reference_id=str(execution.id)
            )
            db.commit()
            db.refresh(wallet)
        except InsufficientBalanceError as exc:
            db.rollback()
            raise HTTPException(status_code=402, detail=str(exc)) from exc

        # Audit Log
        audit_service.log_action(
            db, current_user.id, "run_agent", "agent", str(agent.id),
            details={"input": input_data, "execution_id": execution.id, "cost": cost},
            ip_address=request.client.host
        )

        return {
            "status": execution.status,
            "result": execution.result,
            "cost": cost,
            "remaining_credits": serialize_amount(wallet.balance) if wallet else 0
        }
    except HTTPException:
        # Re-raise HTTP exceptions (from enforcement gate, etc.)
        raise
    except Exception as e:
        logger.error(f"Execution failed: {e}")
        audit_service.log_action(
            db, current_user.id, "run_agent_error", "agent", str(agent.id),
            details={"error": str(e)}, ip_address=request.client.host
        )
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{agent_id}/clone", response_model=AgentSchema)
def clone_agent(agent_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    original = db.query(Agent).filter(Agent.id == agent_id).first()
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

    return process_agent_response(new_agent)

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
        raise HTTPException(status_code=404, detail="Agent not found")

    if agent.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    return db.query(AgentVersion).filter(AgentVersion.agent_id == agent_id).order_by(AgentVersion.created_at.desc()).all()

@router.post("/{agent_id}/rollback/{version_id}", response_model=AgentSchema)
def rollback_version(
    agent_id: int,
    version_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    if agent.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    version = db.query(AgentVersion).filter(
        AgentVersion.id == version_id,
        AgentVersion.agent_id == agent_id
    ).first()
    if not version:
        raise HTTPException(status_code=404, detail="Version not found")

    # Encrypt the version's config and set it as current
    if version.config:
        agent.config = encryption_service.encrypt_data(version.config)
    agent.version = version.version
    db.commit()
    db.refresh(agent)

    return process_agent_response(agent)
