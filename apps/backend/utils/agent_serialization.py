import json
import logging
from typing import Any, Dict, Optional

from models import Agent
from models.monetization import MarketplaceListing
from schemas import Agent as AgentSchema
from schemas import MarketplaceListing as ListingSchema
from services.encryption import encryption_service

logger = logging.getLogger(__name__)


def normalize_agent(agent: Agent) -> Agent:
    if agent is None:
        return agent

    config = agent.config
    if config is None:
        agent.config = {}
    elif isinstance(config, dict):
        agent.config = config
    else:
        try:
            decrypted = encryption_service.decrypt_data(config)
            if isinstance(decrypted, dict):
                agent.config = decrypted
            elif isinstance(decrypted, str):
                try:
                    parsed = json.loads(decrypted)
                    agent.config = parsed if isinstance(parsed, dict) else {}
                except Exception:
                    agent.config = {}
            else:
                agent.config = {}
        except Exception as exc:
            logger.warning("Failed to decrypt agent config: %s", exc)
            agent.config = {}

    skills = agent.skills
    if skills is None:
        return agent
    if isinstance(skills, list):
        return agent
    if isinstance(skills, str):
        try:
            parsed = json.loads(skills)
            if isinstance(parsed, list):
                agent.skills = parsed
            else:
                agent.skills = [s.strip() for s in skills.split(",") if s.strip()]
        except Exception:
            agent.skills = [s.strip() for s in skills.split(",") if s.strip()]
    else:
        agent.skills = []

    return agent


def serialize_agent(agent: Agent) -> Optional[Dict[str, Any]]:
    if agent is None:
        return None

    normalized = normalize_agent(agent)
    try:
        return AgentSchema.model_validate(normalized).model_dump()
    except Exception as exc:
        logger.error(
            "Failed to serialize agent %s: %s",
            getattr(agent, "id", None),
            exc,
            exc_info=True,
        )
        return {
            "id": getattr(agent, "id", None),
            "name": getattr(agent, "name", None) or "Agent",
            "description": getattr(agent, "description", None),
            "config": normalized.config if isinstance(normalized.config, dict) else {},
            "is_published": bool(getattr(agent, "is_published", False)),
            "tags": getattr(agent, "tags", None),
            "category": getattr(agent, "category", None),
            "version": getattr(agent, "version", None) or "1.0.0",
            "role": getattr(agent, "role", None),
            "skills": normalized.skills if isinstance(normalized.skills, list) else [],
            "ai_provider": getattr(agent, "ai_provider", None) or "openai",
            "model_name": getattr(agent, "model_name", None) or "gpt-3.5-turbo",
            "temperature": getattr(agent, "temperature", None)
            if getattr(agent, "temperature", None) is not None
            else 0.7,
            "owner_id": getattr(agent, "owner_id", None),
            "created_at": getattr(agent, "created_at", None),
            "updated_at": getattr(agent, "updated_at", None),
        }


def serialize_listing(listing: MarketplaceListing) -> Optional[Dict[str, Any]]:
    if listing is None:
        return None

    if getattr(listing, "agent", None) is not None:
        normalize_agent(listing.agent)

    try:
        return ListingSchema.model_validate(listing).model_dump()
    except Exception as exc:
        logger.error(
            "Failed to serialize listing %s: %s",
            getattr(listing, "id", None),
            exc,
            exc_info=True,
        )
        return {
            "id": getattr(listing, "id", None),
            "agent_id": getattr(listing, "agent_id", None),
            "listing_type": getattr(listing, "resource_type", None) or "agent",
            "resource_id": getattr(listing, "resource_id", None),
            "seller_id": getattr(listing, "seller_id", None),
            "price": getattr(listing, "price", None) or 0.0,
            "category": getattr(listing, "category", None),
            "is_active": bool(getattr(listing, "is_active", True)),
            "downloads": getattr(listing, "downloads", 0) or 0,
            "rating": getattr(listing, "rating", 0.0) or 0.0,
            "version": getattr(listing, "version", None) or "1.0.0",
            "created_at": getattr(listing, "created_at", None),
            "agent": serialize_agent(getattr(listing, "agent", None)),
        }
