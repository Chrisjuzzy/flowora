from sqlalchemy.orm import Session
from typing import Optional
import logging

from config_production import settings
from models import Agent
from services.encryption import encryption_service

logger = logging.getLogger(__name__)


def ensure_demo_agent(db: Session) -> Agent:
    """
    Ensure a published demo agent exists. Creates one if missing.
    """
    demo_agent = db.query(Agent).filter(
        Agent.name == settings.DEMO_AGENT_NAME,
        Agent.owner_id == None
    ).first()

    if demo_agent:
        if not demo_agent.is_published:
            demo_agent.is_published = True
            db.commit()
            db.refresh(demo_agent)
        return demo_agent

    config_payload = {"system_prompt": settings.DEMO_AGENT_SYSTEM_PROMPT}
    encrypted_config = encryption_service.encrypt_data(config_payload)

    demo_agent = Agent(
        name=settings.DEMO_AGENT_NAME,
        description=settings.DEMO_AGENT_DESCRIPTION,
        config=encrypted_config,
        owner_id=None,
        is_published=True,
        tags="demo,public,flowora",
        category="demo",
        ai_provider=settings.DEFAULT_AI_PROVIDER,
        model_name=settings.DEMO_AGENT_MODEL,
        temperature=0.4
    )
    db.add(demo_agent)
    db.commit()
    db.refresh(demo_agent)
    logger.info("Created demo agent with id %s", demo_agent.id)
    return demo_agent


def get_demo_agent(db: Session) -> Optional[Agent]:
    return db.query(Agent).filter(
        Agent.name == settings.DEMO_AGENT_NAME,
        Agent.owner_id == None,
        Agent.is_published == True
    ).first()
