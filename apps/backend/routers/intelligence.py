from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from typing import List, Optional
from database_production import get_db
from models import AgentMemory, ReflectionLog, SharedKnowledge, SkillEvolution, Agent, AgentMessage, DelegatedTask, WorkspaceMemory, FailurePattern
from services.intelligence_service import KnowledgeService, MessagingDelegationService, WorkspaceMemoryService
from services.workflow_runner import run_swarm
from pydantic import BaseModel
from datetime import datetime
import uuid
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/intelligence", tags=["intelligence"])

# --- Schemas ---
class ReflectionSchema(BaseModel):
    id: int
    execution_id: int
    agent_id: int
    confidence_score: float
    critique: str
    suggestions: str
    is_flagged: bool
    created_at: datetime
    class Config:
        from_attributes = True

class KnowledgeSchema(BaseModel):
    id: int
    topic: str
    content: str
    category: str
    source_agent_id: int
    created_at: datetime
    class Config:
        from_attributes = True

class EvolutionSchema(BaseModel):
    id: int
    agent_id: int
    issue_detected: str
    proposed_prompt: str
    status: str
    created_at: datetime
    class Config:
        from_attributes = True

class FailurePatternSchema(BaseModel):
    id: int
    agent_id: int
    pattern_type: str
    frequency: int
    last_occurred: datetime
    description: str
    class Config:
        from_attributes = True

class DashboardStats(BaseModel):
    total_memories: int
    total_reflections: int
    avg_confidence: float
    flagged_executions: int
    pending_evolutions: int

# --- Endpoints ---

@router.get("/insights", response_model=DashboardStats)
def get_insights(db: Session = Depends(get_db)):
    """Get intelligence insights and statistics"""
    total_memories = db.query(AgentMemory).count()
    total_reflections = db.query(ReflectionLog).count()
    flagged = db.query(ReflectionLog).filter(ReflectionLog.is_flagged == True).count()
    pending = db.query(SkillEvolution).filter(SkillEvolution.status == "pending").count()

    # Avg confidence
    result = db.query(ReflectionLog.confidence_score).all()
    avg_conf = 0.0
    if result:
        avg_conf = sum([r[0] for r in result]) / len(result)

    return {
        "total_memories": total_memories,
        "total_reflections": total_reflections,
        "avg_confidence": avg_conf,
        "flagged_executions": flagged,
        "pending_evolutions": pending
    }

@router.get("/dashboard", response_model=DashboardStats)
def get_dashboard_stats(db: Session = Depends(get_db)):
    total_memories = db.query(AgentMemory).count()
    total_reflections = db.query(ReflectionLog).count()
    flagged = db.query(ReflectionLog).filter(ReflectionLog.is_flagged == True).count()
    pending = db.query(SkillEvolution).filter(SkillEvolution.status == "pending").count()
    
    # Avg confidence
    result = db.query(ReflectionLog.confidence_score).all()
    avg_conf = 0.0
    if result:
        avg_conf = sum([r[0] for r in result]) / len(result)
        
    return {
        "total_memories": total_memories,
        "total_reflections": total_reflections,
        "avg_confidence": avg_conf,
        "flagged_executions": flagged,
        "pending_evolutions": pending
    }

@router.get("/reflections", response_model=List[ReflectionSchema])
def list_reflections(agent_id: Optional[int] = None, flagged_only: bool = False, db: Session = Depends(get_db)):
    query = db.query(ReflectionLog)
    if agent_id:
        query = query.filter(ReflectionLog.agent_id == agent_id)
    if flagged_only:
        query = query.filter(ReflectionLog.is_flagged == True)
    return query.order_by(ReflectionLog.created_at.desc()).limit(50).all()

@router.get("/knowledge", response_model=List[KnowledgeSchema])
def list_knowledge(topic: Optional[str] = None, db: Session = Depends(get_db)):
    if topic:
        return KnowledgeService.get_relevant_knowledge(db, topic)
    return db.query(SharedKnowledge).order_by(SharedKnowledge.created_at.desc()).limit(20).all()

@router.post("/knowledge")
def share_knowledge(agent_id: int, topic: str, content: str, category: str, db: Session = Depends(get_db)):
    return KnowledgeService.share_insight(db, agent_id, topic, content, category)

@router.post("/knowledge/{knowledge_id}/reinforce")
def reinforce_knowledge(knowledge_id: int, db: Session = Depends(get_db)):
    try:
        knowledge = db.query(SharedKnowledge).filter(SharedKnowledge.id == knowledge_id).first()
        if not knowledge:
            return {"status": "not_found", "new_score": 0}
        knowledge.reinforcement_score = (knowledge.reinforcement_score or 0) + 1
        db.commit()
        return {"status": "reinforced", "new_score": knowledge.reinforcement_score}
    except Exception as e:
        logger.error(f"Failed to reinforce knowledge {knowledge_id}: {e}", exc_info=True)
        db.rollback()
        return {"status": "error", "error": str(e), "new_score": 0}

@router.get("/patterns/{agent_id}", response_model=List[FailurePatternSchema])
def get_failure_patterns(agent_id: int, db: Session = Depends(get_db)):
    return db.query(FailurePattern).filter(FailurePattern.agent_id == agent_id).all()

@router.get("/evolutions", response_model=List[EvolutionSchema])
def list_evolutions(status: str = "pending", db: Session = Depends(get_db)):
    return db.query(SkillEvolution).filter(SkillEvolution.status == status).all()

@router.post("/evolutions/{evo_id}/apply")
def apply_evolution(evo_id: int, db: Session = Depends(get_db)):
    evo = db.query(SkillEvolution).filter(SkillEvolution.id == evo_id).first()
    if not evo:
        raise HTTPException(status_code=404, detail="Evolution proposal not found")
        
    agent = db.query(Agent).filter(Agent.id == evo.agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
        
    # Apply new prompt
    if not agent.config:
        agent.config = {}
    
    # Update config (create copy to avoid mutation issues if dict)
    new_config = dict(agent.config)
    new_config["system_prompt"] = evo.proposed_prompt
    agent.config = new_config
    
    # Update version
    try:
        v_parts = agent.version.split('.')
        v_parts[-1] = str(int(v_parts[-1]) + 1)
        agent.version = ".".join(v_parts)
    except Exception:
        agent.version = agent.version + ".1"
        
    evo.status = "applied"
    db.commit()
    return {"status": "success", "new_version": agent.version}

# --- Collaboration APIs ---

class MessageCreate(BaseModel):
    sender_agent_id: int
    receiver_agent_id: int
    content: str

class MessageSchema(BaseModel):
    id: int
    sender_agent_id: int
    receiver_agent_id: int
    content: str
    status: str
    created_at: datetime
    class Config:
        from_attributes = True

@router.post("/messages", response_model=MessageSchema)
def send_message(payload: MessageCreate, db: Session = Depends(get_db)):
    return MessagingDelegationService.send_message(db, payload.sender_agent_id, payload.receiver_agent_id, payload.content)

@router.get("/messages", response_model=List[MessageSchema])
def list_messages(agent_id: int, peer_id: Optional[int] = None, db: Session = Depends(get_db)):
    return MessagingDelegationService.list_messages(db, agent_id, peer_id)

class DelegationCreate(BaseModel):
    parent_agent_id: int
    child_agent_id: int
    goal: str
    input_payload: Optional[str] = None
    priority: int = 5

class DelegationSchema(BaseModel):
    id: int
    parent_agent_id: int
    child_agent_id: int
    goal: str
    input_payload: Optional[str]
    status: str
    priority: int
    result: Optional[str] = None
    created_at: datetime
    class Config:
        from_attributes = True

@router.post("/delegations", response_model=DelegationSchema)
def create_delegation(payload: DelegationCreate, db: Session = Depends(get_db)):
    return MessagingDelegationService.delegate_task(db, payload.parent_agent_id, payload.child_agent_id, payload.goal, payload.input_payload, payload.priority)

class DelegationStatusUpdate(BaseModel):
    status: str
    result: Optional[str] = None

@router.post("/delegations/{task_id}/status", response_model=DelegationSchema)
def update_delegation_status(task_id: int, payload: DelegationStatusUpdate, db: Session = Depends(get_db)):
    try:
        return MessagingDelegationService.update_task_status(db, task_id, payload.status, payload.result)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

class WorkspaceMemoryCreate(BaseModel):
    workspace_id: int
    key: str
    value: str
    author_agent_id: Optional[int] = None

class WorkspaceMemorySchema(BaseModel):
    id: int
    workspace_id: int
    key: str
    value: str
    author_agent_id: Optional[int] = None
    created_at: datetime
    class Config:
        from_attributes = True

@router.post("/workspace_memory", response_model=WorkspaceMemorySchema)
def write_workspace_memory(payload: WorkspaceMemoryCreate, db: Session = Depends(get_db)):
    return WorkspaceMemoryService.write_memory(db, payload.workspace_id, payload.key, payload.value, payload.author_agent_id)

@router.get("/workspace_memory", response_model=List[WorkspaceMemorySchema])
def read_workspace_memory(workspace_id: int, key: Optional[str] = None, db: Session = Depends(get_db)):
    return WorkspaceMemoryService.read_memory(db, workspace_id, key)

class SwarmRequest(BaseModel):
    agent_ids: List[int]
    goal: str
    workspace_id: Optional[int] = None
    max_rounds: int = 3

@router.post("/swarm")
async def swarm_execute(payload: SwarmRequest, db: Session = Depends(get_db)):
    swarm_id = str(uuid.uuid4())
    agent_ids = payload.agent_ids or []
    if not agent_ids:
        # Fallback to any available agents to avoid hard failure
        agent_ids = [a.id for a in db.query(Agent).limit(3).all()]
    if not agent_ids:
        return {
            "swarm_id": swarm_id,
            "agents_used": [],
            "status": "completed",
            "result": {"error": "No agents available"}
        }

    try:
        result = await run_swarm(
            db,
            agent_ids,
            payload.goal,
            payload.workspace_id,
            payload.max_rounds
        )
        return {
            "swarm_id": swarm_id,
            "agents_used": agent_ids,
            "status": "completed",
            "result": result
        }
    except Exception as e:
        logger.error(f"Swarm execution failed: {e}", exc_info=True)
        return {
            "swarm_id": swarm_id,
            "agents_used": agent_ids,
            "status": "completed",
            "result": {"error": str(e)}
        }
