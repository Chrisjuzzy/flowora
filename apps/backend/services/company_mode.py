import json
import logging
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from models import Agent
from services.agent_generator import AgentGenerator
from services.agent_runner import run_agent

logger = logging.getLogger(__name__)

DEFAULT_ROLES = [
    "CEO",
    "Planner",
    "Developer",
    "Marketing",
    "Support"
]


def _extract_json_list(text: str) -> List[str]:
    if not text:
        return []
    start = text.find("[")
    end = text.rfind("]")
    if start == -1 or end == -1 or end <= start:
        return []
    try:
        data = json.loads(text[start : end + 1])
        return [str(item).strip() for item in data if str(item).strip()]
    except Exception:
        return []


class CompanyModeCoordinator:
    def __init__(self, provider_name: str = "openai") -> None:
        self.generator = AgentGenerator(provider_name=provider_name)

    async def ensure_role_agents(
        self,
        db: Session,
        owner_id: Optional[int],
        workspace_id: Optional[int]
    ) -> Dict[str, Agent]:
        agents: Dict[str, Agent] = {}
        for role in DEFAULT_ROLES:
            existing = db.query(Agent).filter(
                Agent.role == role,
                Agent.owner_id == owner_id
            ).first()
            if existing:
                agents[role] = existing
                continue
            agent, _ = await self.generator.generate_agent(
                db=db,
                goal=f"Act as the {role} of an AI company.",
                owner_id=owner_id,
                workspace_id=workspace_id,
                category="company"
            )
            agent.role = role
            db.commit()
            db.refresh(agent)
            agents[role] = agent
        return agents

    async def run_company_mode(
        self,
        db: Session,
        goal: str,
        owner_id: Optional[int],
        workspace_id: Optional[int]
    ) -> Dict[str, any]:
        agents = await self.ensure_role_agents(db, owner_id, workspace_id)
        ceo = agents.get("CEO")
        planner = agents.get("Planner")

        planning_prompt = (
            "Break down the company goal into tasks for the Planner, Developer, Marketing, and Support agents. "
            "Return a JSON array of task strings."
        )
        plan_response = await run_agent(db, planner.id, input_data=f"{planning_prompt}\nGoal: {goal}")
        plan_text = plan_response.get("result", "") if isinstance(plan_response, dict) else getattr(plan_response, "result", "")
        tasks = _extract_json_list(plan_text) or [
            f"Planner: Outline strategy for {goal}",
            f"Developer: Build core workflow for {goal}",
            f"Marketing: Position the product for {goal}",
            f"Support: Prepare FAQs for {goal}"
        ]

        results = []
        role_map = {
            "Planner": agents.get("Planner"),
            "Developer": agents.get("Developer"),
            "Marketing": agents.get("Marketing"),
            "Support": agents.get("Support")
        }

        for task in tasks:
            assigned_role = next((role for role in role_map if role.lower() in task.lower()), "Planner")
            agent = role_map.get(assigned_role)
            if not agent:
                continue
            response = await run_agent(db, agent.id, input_data=f"Task: {task}\nGoal: {goal}")
            output = response.get("result", "") if isinstance(response, dict) else getattr(response, "result", "")
            results.append({"role": assigned_role, "task": task, "output": output})

        summary_prompt = (
            "Summarize the team outputs into a final plan. "
            "Return JSON with fields: `summary` and `next_actions` (array)."
        )
        summary_res = await run_agent(db, ceo.id, input_data=f"{summary_prompt}\nGoal: {goal}\nOutputs: {results}")
        summary_text = summary_res.get("result", "") if isinstance(summary_res, dict) else getattr(summary_res, "result", "")

        return {
            "goal": goal,
            "roles": {role: agent.id for role, agent in agents.items()},
            "tasks": results,
            "summary": summary_text
        }
