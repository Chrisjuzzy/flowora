import json
import logging
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from models import Agent, AgentTemplate, AgentVersion
from services.ai_provider_service import AIProviderFactory
from services.encryption import encryption_service
from services.agent_runtime.planner import PlanGenerator
from services.tool_permissions import ToolPermissionService
from tools.tool_registry import tool_registry

logger = logging.getLogger(__name__)


def _extract_json_object(text: str) -> Optional[dict]:
    if not text:
        return None
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    try:
        return json.loads(text[start : end + 1])
    except Exception:
        return None


class AgentGenerator:
    def __init__(self, provider_name: str = "openai") -> None:
        self.provider_name = provider_name
        self.planner = PlanGenerator(max_steps=6)

    def _select_template(self, db: Session, goal: str, category: Optional[str] = None) -> Optional[AgentTemplate]:
        query = db.query(AgentTemplate).filter(AgentTemplate.is_active == True)
        if category:
            query = query.filter(AgentTemplate.category == category)
        template = query.first()
        if template:
            return template
        # Fallback: keyword match on goal
        for candidate in query.all():
            if candidate.name.lower() in goal.lower():
                return candidate
        return None

    async def _generate_spec(
        self,
        goal: str,
        template: Optional[AgentTemplate],
        tools: List[str]
    ) -> Dict[str, Any]:
        provider = AIProviderFactory.get_provider(self.provider_name)
        template_context = ""
        if template:
            template_context = f"Template: {template.name}. {template.description}. Base config: {template.base_config}"

        prompt = (
            "Generate an agent specification as JSON with fields: "
            "`name`, `description`, `system_prompt`, `tools` (array), "
            "`category`, `tags` (array), `role`, `skills` (array), "
            "`memory` (short_term/long_term/vector), `model_name`, `temperature`, `max_steps`.\n\n"
            f"Goal: {goal}\n"
            f"Available tools: {', '.join(tools) if tools else 'none'}\n"
            f"{template_context}"
        )

        try:
            response = await provider.generate_with_metadata(prompt)
            return _extract_json_object(response.get("text", "")) or {}
        except Exception as exc:
            logger.warning("Agent spec generation failed: %s", exc)
            return {}

    def _normalize_tools(self, tools: Any) -> List[str]:
        available = set(tool_registry.list_tools().keys())
        if isinstance(tools, str):
            candidate = [t.strip() for t in tools.split(",") if t.strip()]
        elif isinstance(tools, list):
            candidate = [str(t).strip() for t in tools if str(t).strip()]
        else:
            candidate = []
        return [t for t in candidate if t in available]

    async def generate_agent(
        self,
        db: Session,
        goal: str,
        owner_id: Optional[int] = None,
        workspace_id: Optional[int] = None,
        category: Optional[str] = None
    ) -> Tuple[Agent, Dict[str, Any]]:
        template = self._select_template(db, goal, category)
        available_tools = list(tool_registry.list_tools().keys())
        spec = await self._generate_spec(goal, template, available_tools)

        if not spec:
            spec = {
                "name": f"Autonomous Agent for {goal[:32]}",
                "description": f"Auto-generated agent for goal: {goal}",
                "system_prompt": f"You are an expert agent. Goal: {goal}",
                "tools": available_tools[:3],
                "category": category or (template.category if template else "general"),
                "tags": ["autonomous"],
                "role": "Autonomous",
                "skills": ["planning", "execution"],
                "memory": "vector",
                "model_name": "gpt-4o-mini",
                "temperature": 0.4,
                "max_steps": 4
            }

        tools = self._normalize_tools(spec.get("tools") or (template.tools if template else []))
        plan = await self.planner.build_plan(
            AIProviderFactory.get_provider(self.provider_name),
            goal,
            system_prompt=spec.get("system_prompt", "You are a helpful agent."),
            tool_names=tools
        )

        config = {
            "system_prompt": spec.get("system_prompt", "You are a helpful agent."),
            "tools": tools,
            "memory": spec.get("memory", "vector"),
            "max_steps": int(spec.get("max_steps", 4)),
            "generation_plan": [p.description for p in plan]
        }

        encrypted_config = encryption_service.encrypt_data(config)

        agent = Agent(
            name=spec.get("name", f"Autonomous Agent {goal[:20]}"),
            description=spec.get("description", goal),
            config=encrypted_config,
            owner_id=owner_id,
            category=spec.get("category") or (template.category if template else None),
            tags=",".join(spec.get("tags") or []),
            role=spec.get("role"),
            skills=spec.get("skills"),
            ai_provider=self.provider_name,
            model_name=spec.get("model_name", "gpt-4o-mini"),
            temperature=float(spec.get("temperature", 0.4)),
            workspace_id=workspace_id
        )
        db.add(agent)
        db.commit()
        db.refresh(agent)

        # Store version snapshot for prompt versioning
        db.add(
            AgentVersion(
                agent_id=agent.id,
                version=agent.version,
                config=config,
                description="Auto-generated agent configuration"
            )
        )
        db.commit()

        ToolPermissionService.ensure_permissions(db, agent.id, tools)

        payload = {
            "agent_id": agent.id,
            "plan": [p.description for p in plan],
            "tools": tools,
            "capabilities": spec.get("skills") or spec.get("capabilities") or []
        }
        return agent, payload
