from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session

from database_production import get_db
from security import get_current_user
from models import AgentTemplate
from services.agent_generator import AgentGenerator
from services.agent_optimizer import AgentOptimizer
from services.product_generator import AIProductGenerator
from services.autonomous_workflows import WorkflowAutogenService
from services.company_mode import CompanyModeCoordinator
from services.marketplace_autopublish import MarketplaceAutopublishService
from services.tool_permissions import ToolPermissionService
from celery_app import celery_app
from services.queue_protection import enqueue_task
from config_production import settings

router = APIRouter(prefix="/autonomy", tags=["autonomy"])


class AgentGenerationRequest(BaseModel):
    goal: str
    workspace_id: Optional[int] = None
    category: Optional[str] = None
    auto_publish: bool = False


class WorkflowGenerationRequest(BaseModel):
    goal: str
    workspace_id: Optional[int] = None


class CompanyModeRequest(BaseModel):
    goal: str
    workspace_id: Optional[int] = None


class ProductGenerationRequest(BaseModel):
    goal: str
    workspace_id: Optional[int] = None


class TemplateCreateRequest(BaseModel):
    name: str
    description: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[str] = None
    base_config: Optional[dict] = None
    tools: Optional[list] = None


class ToolPermissionRequest(BaseModel):
    tools: list[str]


@router.post("/agent-generation")
async def generate_agent(
    payload: AgentGenerationRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    generator = AgentGenerator()
    agent, details = await generator.generate_agent(
        db,
        goal=payload.goal,
        owner_id=current_user.id,
        workspace_id=payload.workspace_id,
        category=payload.category
    )
    listing = None
    if payload.auto_publish:
        publisher = MarketplaceAutopublishService()
        listing = publisher.publish_agent(
            db,
            agent_id=agent.id,
            seller_id=current_user.id,
            price=19.0,
            category=payload.category,
            auto=True,
            capabilities=details.get("capabilities"),
            pricing_tier="standard"
        )
    return {
        "status": "created",
        "agent_id": agent.id,
        "plan": details.get("plan", []),
        "tools": details.get("tools", []),
        "marketplace_listing_id": listing.id if listing else None
    }


@router.post("/agents/{agent_id}/optimize")
async def optimize_agent(
    agent_id: int,
    async_execution: bool = True,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    if settings.ENABLE_ASYNC_EXECUTION and async_execution:
        task = enqueue_task(
            "tasks.optimization_tasks.optimize_agent",
            args=[{"agent_id": agent_id, "min_runs": 5}],
            queue="optimization"
        )
        return {"status": "queued", "task_id": task.id}

    optimizer = AgentOptimizer()
    agent, metrics = await optimizer.optimize_agent_prompt(db, agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return {
        "status": "optimized",
        "agent_id": agent.id,
        "version": agent.version,
        "metrics": metrics
    }


@router.post("/agents/{agent_id}/tools")
def set_agent_tools(
    agent_id: int,
    payload: ToolPermissionRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    tools = ToolPermissionService.set_allowed_tools(db, agent_id, payload.tools)
    return {"status": "updated", "agent_id": agent_id, "tools": tools}


@router.post("/products/generate")
async def generate_product(
    payload: ProductGenerationRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    generator = AIProductGenerator()
    result = await generator.generate_product(
        db,
        goal=payload.goal,
        owner_id=current_user.id,
        workspace_id=payload.workspace_id
    )
    return result


@router.post("/workflows/generate")
async def generate_workflow(
    payload: WorkflowGenerationRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    service = WorkflowAutogenService()
    workflow = await service.generate_workflow(db, payload.goal, owner_id=current_user.id)
    return {
        "status": "created",
        "workflow_id": workflow.id,
        "name": workflow.name
    }


@router.post("/company/run")
async def company_mode(
    payload: CompanyModeRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    coordinator = CompanyModeCoordinator()
    return await coordinator.run_company_mode(
        db,
        goal=payload.goal,
        owner_id=current_user.id,
        workspace_id=payload.workspace_id
    )


@router.get("/templates")
def list_templates(db: Session = Depends(get_db)):
    templates = db.query(AgentTemplate).filter(AgentTemplate.is_active == True).all()
    return [
        {
            "id": t.id,
            "name": t.name,
            "description": t.description,
            "category": t.category,
            "version": t.version,
            "tags": t.tags
        }
        for t in templates
    ]


@router.post("/templates")
def create_template(
    payload: TemplateCreateRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    template = AgentTemplate(
        name=payload.name,
        description=payload.description,
        category=payload.category,
        tags=payload.tags,
        base_config=payload.base_config,
        tools=payload.tools,
        created_by=current_user.id
    )
    db.add(template)
    db.commit()
    db.refresh(template)
    return {
        "status": "created",
        "template_id": template.id
    }
