from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from datetime import datetime
import re

from database_production import get_db
from security import get_current_user
from models import AgentTemplate, AgentTemplateStats, WorkflowTemplate, ToolConfigTemplate, User, Agent
from services.encryption import encryption_service
from utils.agent_serialization import serialize_agent
from config_production import settings

router = APIRouter(prefix="/templates", tags=["templates"])


class AgentTemplateCreate(BaseModel):
    name: str
    description: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[str] = None
    base_config: Optional[dict] = None
    tools: Optional[list] = None


class AgentTemplateSubmit(BaseModel):
    agent_id: int
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[str] = None


class WorkflowTemplateCreate(BaseModel):
    name: str
    description: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[str] = None
    config_json: Optional[dict] = None


class ToolConfigTemplateCreate(BaseModel):
    name: str
    description: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[str] = None
    tool_config: Optional[dict] = None


DEFAULT_AGENT_TEMPLATES: List[Dict[str, Any]] = [
    {
        "name": "Startup Idea Generator",
        "description": "Generate viable startup ideas with target markets and differentiation.",
        "category": "growth",
        "tags": "startup,ideas,market",
        "base_config": {
            "system_prompt": "You are a startup idea generator focused on viable, scalable ideas.",
            "prompt": "Generate three startup ideas for {input}. Include a target market and differentiator.",
            "tools": ["web_search", "http_request"],
            "max_steps": 3,
            "temperature": 0.4
        }
    },
    {
        "name": "Marketing Content Agent",
        "description": "Create launch messaging, ads, and social content for new products.",
        "category": "marketing",
        "tags": "marketing,launch,content",
        "base_config": {
            "system_prompt": "You are a marketing strategist creating launch content.",
            "prompt": "Create launch messaging and three social posts for {input}.",
            "tools": ["web_search"],
            "max_steps": 3,
            "temperature": 0.5
        }
    },
    {
        "name": "Twitter Thread Writer",
        "description": "Craft high-retention Twitter/X threads with hooks and CTAs.",
        "category": "marketing",
        "tags": "twitter,threads,copywriting",
        "base_config": {
            "system_prompt": "You write viral Twitter threads with clear structure.",
            "prompt": "Write a 7-tweet thread about {input} with a strong hook and CTA.",
            "tools": [],
            "max_steps": 3,
            "temperature": 0.6
        }
    },
    {
        "name": "Business Plan Generator",
        "description": "Generate concise business plans with market, product, and go-to-market.",
        "category": "strategy",
        "tags": "business,plan,gtm",
        "base_config": {
            "system_prompt": "You are a business plan writer for early-stage founders.",
            "prompt": "Create a 1-page business plan for {input}. Include market, product, and GTM.",
            "tools": ["web_search"],
            "max_steps": 4,
            "temperature": 0.4
        }
    },
    {
        "name": "Blog Post Generator",
        "description": "Outline and draft long-form blog posts with SEO-friendly structure.",
        "category": "content",
        "tags": "blog,seo,content",
        "base_config": {
            "system_prompt": "You are a long-form blog writer focused on SEO.",
            "prompt": "Outline and draft a blog post about {input} with headings and key points.",
            "tools": ["web_search"],
            "max_steps": 4,
            "temperature": 0.5
        }
    },
    {
        "name": "Cold Email Writer",
        "description": "Write personalized cold emails with crisp CTAs.",
        "category": "sales",
        "tags": "sales,email,outreach",
        "base_config": {
            "system_prompt": "You craft concise cold emails tailored to the recipient.",
            "prompt": "Write a cold email for {input} with a clear CTA.",
            "tools": [],
            "max_steps": 3,
            "temperature": 0.4
        }
    },
]


def _slugify(text: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", text.lower()).strip("-")
    return slug or "template"


def _ensure_seed_templates(db: Session) -> None:
    existing = {t.name.lower(): t for t in db.query(AgentTemplate).all()}
    created = False
    for payload in DEFAULT_AGENT_TEMPLATES:
        name_key = payload["name"].lower()
        if name_key in existing:
            continue
        template = AgentTemplate(
            name=payload["name"],
            description=payload.get("description"),
            category=payload.get("category"),
            tags=payload.get("tags"),
            base_config=payload.get("base_config"),
            tools=payload.get("base_config", {}).get("tools"),
            created_by=None,
            is_active=True
        )
        db.add(template)
        created = True
    if created:
        db.commit()


def _get_or_create_stats(db: Session, template_id: int) -> AgentTemplateStats:
    stats = db.query(AgentTemplateStats).filter(AgentTemplateStats.template_id == template_id).first()
    if stats:
        return stats
    stats = AgentTemplateStats(template_id=template_id)
    db.add(stats)
    db.commit()
    db.refresh(stats)
    return stats


def _serialize_agent_template(template: AgentTemplate) -> dict:
    stats = template.stats or None
    slug = _slugify(template.name)
    creator_payload = None
    if template.creator:
        creator_payload = {"id": template.creator.id, "email": template.creator.email}
    return {
        "id": template.id,
        "name": template.name,
        "description": template.description,
        "category": template.category,
        "tags": template.tags,
        "version": template.version,
        "is_active": template.is_active,
        "base_config": template.base_config,
        "tools": template.tools,
        "created_at": template.created_at.isoformat() if template.created_at else None,
        "creator": creator_payload,
        "slug": slug,
        "share_url": f"/templates/{slug}",
        "install_count": stats.install_count if stats else 0,
        "share_count": stats.share_count if stats else 0
    }


def _serialize_template(template):
    payload = {
        "id": template.id,
        "name": template.name,
        "description": template.description,
        "category": template.category,
        "tags": template.tags,
        "version": template.version,
        "is_active": template.is_active
    }
    if hasattr(template, "base_config"):
        payload["base_config"] = template.base_config
        payload["tools"] = template.tools
    if hasattr(template, "config_json"):
        payload["config_json"] = template.config_json
    if hasattr(template, "tool_config"):
        payload["tool_config"] = template.tool_config
    return payload


@router.get("/")
def list_all_templates(db: Session = Depends(get_db)):
    _ensure_seed_templates(db)
    return {
        "agents": [_serialize_agent_template(t) for t in db.query(AgentTemplate).filter(AgentTemplate.is_active == True).all()],
        "workflows": [_serialize_template(t) for t in db.query(WorkflowTemplate).filter(WorkflowTemplate.is_active == True).all()],
        "tools": [_serialize_template(t) for t in db.query(ToolConfigTemplate).filter(ToolConfigTemplate.is_active == True).all()]
    }


@router.get("/agents")
def list_agent_templates(db: Session = Depends(get_db)):
    _ensure_seed_templates(db)
    templates = db.query(AgentTemplate).filter(AgentTemplate.is_active == True).order_by(AgentTemplate.created_at.desc()).all()
    return [_serialize_agent_template(t) for t in templates]


@router.get("/agents/by-slug/{slug}")
def get_agent_template_by_slug(slug: str, db: Session = Depends(get_db)):
    _ensure_seed_templates(db)
    if slug.isdigit():
        template = db.query(AgentTemplate).filter(AgentTemplate.id == int(slug)).first()
        if template:
            return _serialize_agent_template(template)
    templates = db.query(AgentTemplate).filter(AgentTemplate.is_active == True).all()
    for template in templates:
        if _slugify(template.name) == slug:
            return _serialize_agent_template(template)
    raise HTTPException(status_code=404, detail="Template not found")


@router.post("/agents")
def create_agent_template(
    payload: AgentTemplateCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
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
    _get_or_create_stats(db, template.id)
    return _serialize_agent_template(template)


@router.post("/agents/submit")
def submit_agent_template(
    payload: AgentTemplateSubmit,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    agent = db.query(Agent).filter(Agent.id == payload.agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    if agent.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to submit this agent")

    base_config = {}
    if agent.config:
        try:
            base_config = encryption_service.decrypt_data(agent.config)
        except Exception:
            base_config = {}

    template = AgentTemplate(
        name=payload.name or agent.name,
        description=payload.description or agent.description,
        category=payload.category or agent.category,
        tags=payload.tags or agent.tags,
        base_config=base_config,
        tools=base_config.get("tools"),
        created_by=current_user.id
    )
    db.add(template)
    db.commit()
    db.refresh(template)
    _get_or_create_stats(db, template.id)
    return _serialize_agent_template(template)


@router.post("/agents/{template_id}/install")
def install_agent_template(
    template_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    template = db.query(AgentTemplate).filter(AgentTemplate.id == template_id, AgentTemplate.is_active == True).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    base_config = template.base_config or {}
    encrypted_config = encryption_service.encrypt_data(base_config) if base_config else None
    temperature = base_config.get("temperature", 0.4)

    new_agent = Agent(
        name=f"{template.name} (Installed)",
        description=template.description,
        config=encrypted_config,
        owner_id=current_user.id,
        category=template.category,
        tags=template.tags,
        ai_provider=settings.DEFAULT_AI_PROVIDER,
        model_name=settings.DEFAULT_AI_MODEL,
        temperature=temperature
    )
    db.add(new_agent)

    stats = _get_or_create_stats(db, template.id)
    stats.install_count = (stats.install_count or 0) + 1
    stats.last_installed_at = datetime.utcnow()

    db.commit()
    db.refresh(new_agent)

    return {
        "message": "Template installed",
        "agent": serialize_agent(new_agent),
        "install_count": stats.install_count
    }


@router.post("/agents/{template_id}/share")
def share_agent_template(template_id: int, db: Session = Depends(get_db)):
    template = db.query(AgentTemplate).filter(AgentTemplate.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    stats = _get_or_create_stats(db, template.id)
    stats.share_count = (stats.share_count or 0) + 1
    db.commit()
    db.refresh(stats)
    return {"share_count": stats.share_count}


@router.get("/workflows")
def list_workflow_templates(db: Session = Depends(get_db)):
    return [_serialize_template(t) for t in db.query(WorkflowTemplate).filter(WorkflowTemplate.is_active == True).all()]


@router.post("/workflows")
def create_workflow_template(
    payload: WorkflowTemplateCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    template = WorkflowTemplate(
        name=payload.name,
        description=payload.description,
        category=payload.category,
        tags=payload.tags,
        config_json=payload.config_json,
        created_by=current_user.id
    )
    db.add(template)
    db.commit()
    db.refresh(template)
    return _serialize_template(template)


@router.get("/tools")
def list_tool_templates(db: Session = Depends(get_db)):
    return [_serialize_template(t) for t in db.query(ToolConfigTemplate).filter(ToolConfigTemplate.is_active == True).all()]


@router.post("/tools")
def create_tool_template(
    payload: ToolConfigTemplateCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    template = ToolConfigTemplate(
        name=payload.name,
        description=payload.description,
        category=payload.category,
        tags=payload.tags,
        tool_config=payload.tool_config,
        created_by=current_user.id
    )
    db.add(template)
    db.commit()
    db.refresh(template)
    return _serialize_template(template)
