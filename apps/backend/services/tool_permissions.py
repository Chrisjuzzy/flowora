from typing import List, Optional
import logging

from sqlalchemy.orm import Session

from models import Agent, AgentToolPermission
from services.encryption import encryption_service

logger = logging.getLogger(__name__)


class ToolPermissionService:
    @staticmethod
    def get_allowed_tools(db: Session, agent_id: int) -> List[str]:
        permissions = (
            db.query(AgentToolPermission)
            .filter(AgentToolPermission.agent_id == agent_id, AgentToolPermission.is_allowed == True)
            .all()
        )
        if permissions:
            return [p.tool_name for p in permissions]

        agent = db.query(Agent).filter(Agent.id == agent_id).first()
        if not agent or not agent.config:
            return []

        config = agent.config
        if isinstance(config, str):
            try:
                config = encryption_service.decrypt_data(config)
            except Exception:
                config = {}

        tools_value = config.get("tools") if isinstance(config, dict) else None
        if isinstance(tools_value, str):
            return [t.strip() for t in tools_value.split(",") if t.strip()]
        if isinstance(tools_value, list):
            return [str(t).strip() for t in tools_value if str(t).strip()]
        return []

    @staticmethod
    def set_allowed_tools(db: Session, agent_id: int, tools: List[str]) -> List[str]:
        db.query(AgentToolPermission).filter(AgentToolPermission.agent_id == agent_id).delete()
        cleaned = [t.strip() for t in tools if t and t.strip()]
        for tool in cleaned:
            db.add(AgentToolPermission(agent_id=agent_id, tool_name=tool, is_allowed=True))
        db.commit()
        return cleaned

    @staticmethod
    def ensure_permissions(db: Session, agent_id: int, tools: Optional[List[str]]) -> List[str]:
        if tools is None:
            return ToolPermissionService.get_allowed_tools(db, agent_id)
        return ToolPermissionService.set_allowed_tools(db, agent_id, tools)
