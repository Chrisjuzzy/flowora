import json
import logging
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from models import Workflow
from services.ai_provider_service import AIProviderFactory
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


class WorkflowAutogenService:
    def __init__(self, provider_name: str = "openai") -> None:
        self.provider_name = provider_name

    async def generate_workflow(self, db: Session, goal: str, owner_id: Optional[int] = None) -> Workflow:
        provider = AIProviderFactory.get_provider(self.provider_name)
        tools = ", ".join(tool_registry.list_tools().keys())
        prompt = (
            "Generate a workflow graph for the goal. "
            "Return JSON with fields: `name`, `nodes`, `edges`. "
            "Each node should include id, type, label, and optionally agent_id. "
            "Edges should include source and target.\n\n"
            f"Goal: {goal}\n"
            f"Available tools: {tools}"
        )
        response = await provider.generate_with_metadata(prompt)
        data = _extract_json_object(response.get("text", "")) or {}

        name = data.get("name") or f"Auto Workflow: {goal[:32]}"
        nodes = data.get("nodes") or [
            {"id": "start", "type": "input", "label": "Trigger"},
            {"id": "agent-1", "type": "agent", "label": "Primary Agent"},
            {"id": "end", "type": "output", "label": "Output"}
        ]
        edges = data.get("edges") or [
            {"source": "start", "target": "agent-1"},
            {"source": "agent-1", "target": "end"}
        ]

        workflow = Workflow(
            name=name,
            config_json={"nodes": nodes, "edges": edges},
            owner_id=owner_id
        )
        db.add(workflow)
        db.commit()
        db.refresh(workflow)
        return workflow
