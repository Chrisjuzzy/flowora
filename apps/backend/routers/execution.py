from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database_production import get_db
from models import Execution, Agent, User
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime
from security import get_current_user

router = APIRouter(prefix="/executions", tags=["executions"])

class ExecutionSchema(BaseModel):
    id: int
    agent_id: int
    prompt_version_id: Optional[int] = None
    status: str
    result: str
    timestamp: datetime

    class Config:
        from_attributes = True

@router.get("/", response_model=List[ExecutionSchema])
def list_executions(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """List all executions for the current user"""
    executions = db.query(Execution).join(Agent).filter(Agent.owner_id == current_user.id).order_by(Execution.timestamp.desc()).all()
    return executions

@router.get("/{agent_id}", response_model=List[ExecutionSchema])
def get_agent_executions(agent_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # Check if agent exists
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        agent = db.query(Agent).filter(Agent.owner_id == current_user.id).first()
    if not agent:
        return []
        
    executions = db.query(Execution).filter(Execution.agent_id == agent.id).order_by(Execution.timestamp.desc()).all()
    return executions
