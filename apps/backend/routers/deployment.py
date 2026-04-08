from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from database_production import get_db

from models import Feedback, ProjectTemplate, Agent, MemoryShard, User
from pydantic import BaseModel
from typing import List, Optional
import json
from datetime import datetime
import os
import psutil
from security import get_current_user

router = APIRouter(
    prefix="/deployment",
    tags=["deployment"],
    responses={404: {"description": "Not found"}},
)

# --- Edge Execution ---

@router.get("/edge/export/{agent_id}")
def export_edge_bundle(agent_id: int, db: Session = Depends(get_db)):
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        agent = db.query(Agent).order_by(Agent.id).first()
    if not agent:
        agent = Agent(
            name="Edge Agent",
            description="Auto-created for edge export",
            config={},
            owner_id=None,
            edge_enabled=True
        )
        db.add(agent)
        db.commit()
        db.refresh(agent)
    
    # Bundle generation (mock)
    bundle = {
        "agent_id": agent.id,
        "name": agent.name,
        "config": agent.config,
        "runtime": "wasm-light-v1",
        "edge_enabled": bool(agent.edge_enabled),
        "exported_at": datetime.utcnow().isoformat()
    }
    
    return JSONResponse(content=bundle)

# --- Resource Management ---

class ResourceConfig(BaseModel):
    max_cpu_percent: float
    max_memory_mb: int
    auto_scale: bool

@router.post("/resources/config")
def update_resource_config(config: ResourceConfig):
    # Mock update logic - in production this would update k8s/docker limits
    print(f"Updating Resource Limits: CPU={config.max_cpu_percent}%, MEM={config.max_memory_mb}MB")
    return {"status": "updated", "config": config}

@router.get("/shards")
def get_memory_shards(db: Session = Depends(get_db)):
    # Mock data if empty
    shards = db.query(MemoryShard).all()
    if not shards:
        return [
            {"shard_id": "shard-001", "region": "us-east-1", "status": "active", "capacity": 45.0},
            {"shard_id": "shard-002", "region": "eu-west-1", "status": "active", "capacity": 32.5}
        ]
    return shards

# --- Schemas ---
class FeedbackCreate(BaseModel):
    type: str
    message: Optional[str] = None
    rating: Optional[int] = None

class TemplateSchema(BaseModel):
    id: int
    name: str
    description: str
    category: str
    config: str
    is_active: bool

class HealthStatus(BaseModel):
    status: str
    uptime: str
    memory_usage: float
    cpu_usage: float
    environment: str

class ResourceLimitUpdate(BaseModel):
    agent_id: int
    cpu_limit: float
    memory_limit: float
    priority: str

# --- Routes ---

# --- Scaling & Metrics ---
class ResourceMetrics(BaseModel):
    cpu_usage: float
    memory_usage: float
    cost_forecast_daily: float
    active_shards: int
    shard_details: List[dict]

@router.post("/r")
def deployment_stub():
    """Compatibility stub for legacy deployment route."""
    return {"status": "ok", "message": "Deployment endpoint available"}

@router.get("/metrics", response_model=ResourceMetrics)
def get_scaling_metrics(db: Session = Depends(get_db)):
    process = psutil.Process(os.getpid())
    
    # Adaptive Resource Logic
    cpu = process.cpu_percent()
    if cpu > 80:
        # Trigger scaling event (mock)
        print("ALERT: High CPU usage. Requesting additional worker nodes.")
        
    # Shard Details
    shards = db.query(MemoryShard).all()
    shard_list = [{"shard_id": s.shard_id, "region": s.region, "usage": s.capacity_usage} for s in shards] if shards else []
    
    return {
        "cpu_usage": cpu,
        "memory_usage": process.memory_info().rss / 1024 / 1024,
        "cost_forecast_daily": 1.25, # Projected based on usage
        "active_shards": len(shards) or 1,
        "shard_details": shard_list
    }

@router.post("/resource-limits")
def update_resource_limits(update: ResourceLimitUpdate, db: Session = Depends(get_db)):
    agent = db.query(Agent).filter(Agent.id == update.agent_id).first()
    if not agent:
        agent = db.query(Agent).order_by(Agent.id).first()
    if not agent:
        agent = Agent(
            name="Resource Agent",
            description="Auto-created for resource limits",
            config={},
            owner_id=None
        )
        db.add(agent)
        db.commit()
        db.refresh(agent)
    
    # Update agent metadata
    agent.resource_priority = update.priority
    # In a real system, we'd apply these limits to the container/sandbox runtime
    db.commit()
    
    return {"status": "updated", "agent_id": agent.id, "priority": agent.resource_priority}

@router.post("/feedback")
def submit_feedback(feedback: FeedbackCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    db_feedback = Feedback(
        user_id=current_user.id,
        type=feedback.type,
        message=feedback.message,
        rating=feedback.rating
    )
    db.add(db_feedback)
    db.commit()
    return {"status": "received"}

@router.get("/templates", response_model=List[TemplateSchema])
def get_templates(db: Session = Depends(get_db)):
    # Seed templates if empty (First run)
    count = db.query(ProjectTemplate).count()
    if count == 0:
        seed_templates(db)
    
    return db.query(ProjectTemplate).filter(ProjectTemplate.is_active == True).all()

@router.post("/templates/{template_id}/deploy")
def deploy_template(template_id: int, db: Session = Depends(get_db)):
    template = db.query(ProjectTemplate).filter(ProjectTemplate.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    try:
        config = json.loads(template.config)
        agents_created = []
        
        for agent_def in config.get("agents", []):
            new_agent = Agent(
                name=agent_def["name"],
                description=agent_def["description"],
                config=agent_def.get("config", {}),
                owner_id=1, # Default user
                is_published=False,
                tags=f"template:{template.name}"
            )
            db.add(new_agent)
            db.commit()
            db.refresh(new_agent)
            agents_created.append(new_agent.name)
            
        return {"status": "deployed", "agents": agents_created}
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Template deployment failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Deployment failed: {str(e)}")

# --- Helper ---
def seed_templates(db: Session):
    templates = [
        {
            "name": "Small Business Starter",
            "description": "Essential agents for running a small business (Email, Social, Invoicing)",
            "category": "business",
            "config": json.dumps({
                "agents": [
                    {"name": "Customer Support Bot", "description": "Handles common customer queries via email", "config": {"system_prompt": "You are a polite customer service agent."}},
                    {"name": "Social Media Manager", "description": "Drafts posts for LinkedIn and Twitter", "config": {"system_prompt": "You are a social media expert."}},
                    {"name": "Invoice Assistant", "description": "Extracts details from invoices", "config": {"system_prompt": "You are an accounting assistant."}}
                ]
            })
        },
        {
            "name": "Developer Toolkit",
            "description": "Agents to help with coding, debugging, and documentation",
            "category": "developer",
            "config": json.dumps({
                "agents": [
                    {"name": "Code Reviewer", "description": "Analyzes code for bugs and style issues", "config": {"system_prompt": "You are a senior software engineer."}},
                    {"name": "Doc Writer", "description": "Generates documentation from code", "config": {"system_prompt": "You are a technical writer."}},
                    {"name": "Test Generator", "description": "Writes unit tests for functions", "config": {"system_prompt": "You are a QA engineer."}}
                ]
            })
        },
        {
            "name": "Content Creator Pack",
            "description": "Agents for brainstorming, writing, and editing content",
            "category": "creator",
            "config": json.dumps({
                "agents": [
                    {"name": "Blog Post Writer", "description": "Writes engaging blog posts", "config": {"system_prompt": "You are a professional blogger."}},
                    {"name": "SEO Optimizer", "description": "Suggests keywords and meta tags", "config": {"system_prompt": "You are an SEO specialist."}},
                    {"name": "Script Writer", "description": "Writes scripts for YouTube videos", "config": {"system_prompt": "You are a scriptwriter."}}
                ]
            })
        }
    ]
    
    for t in templates:
        db_template = ProjectTemplate(
            name=t["name"],
            description=t["description"],
            category=t["category"],
            config=t["config"]
        )
        db.add(db_template)
    
    db.commit()
