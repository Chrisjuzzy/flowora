import json
import logging
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from services.ai_provider_service import AIProviderFactory
from services.agent_generator import AgentGenerator
from services.autonomous_workflows import WorkflowAutogenService
from services.product_generator import AIProductGenerator
from services.marketplace_autopublish import MarketplaceAutopublishService
from services.analytics_service import AnalyticsService

logger = logging.getLogger(__name__)


def _extract_json(text: str) -> Optional[Any]:
    if not text:
        return None
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(text[start : end + 1])
        except Exception:
            return None
    start = text.find("[")
    end = text.rfind("]")
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(text[start : end + 1])
        except Exception:
            return None
    return None


class FounderController:
    def __init__(self, provider_name: str = "openai") -> None:
        self.provider_name = provider_name
        self.provider = AIProviderFactory.get_provider(provider_name)
        self.agent_generator = AgentGenerator(provider_name=provider_name)
        self.workflow_service = WorkflowAutogenService(provider_name=provider_name)
        self.product_generator = AIProductGenerator(provider_name=provider_name)
        self.publisher = MarketplaceAutopublishService()

    async def _run_role(self, role: str, instructions: str, startup_goal: str) -> str:
        system_prompt = f"You are the {role} agent in a startup founding team."
        prompt = f"{instructions}\n\nStartup goal: {startup_goal}\nReturn concise, actionable output."
        try:
            result = await self.provider.generate_with_metadata(prompt, system_prompt=system_prompt)
            return result.get("text", "").strip()
        except Exception as exc:
            logger.warning("Founder role %s failed: %s", role, exc)
            return ""

    async def run_founder_mode(
        self,
        db: Session,
        startup_goal: str,
        owner_id: Optional[int],
        workspace_id: Optional[int] = None
    ) -> Dict[str, Any]:
        ceo_instructions = (
            "Define product vision, target markets, and go-to-market strategy. "
            "Provide a 5-7 bullet strategy summary."
        )
        pm_instructions = (
            "Create a product roadmap with 3 phases. "
            "Include key features and workflow design priorities."
        )
        marketing_instructions = (
            "Generate a list of marketing assets: blog post titles, landing page headline, "
            "and 3 social posts. Return JSON list if possible."
        )
        growth_instructions = (
            "Generate viral template ideas and marketplace positioning suggestions. "
            "Return JSON list if possible."
        )
        analytics_instructions = (
            "Analyze execution logs and suggest improvements and KPIs. "
            "Return concise improvement recommendations."
        )

        strategy = await self._run_role("CEO", ceo_instructions, startup_goal)
        product_plan = await self._run_role("Product Manager", pm_instructions, startup_goal)
        marketing_text = await self._run_role("Marketing", marketing_instructions, startup_goal)
        growth_text = await self._run_role("Growth", growth_instructions, startup_goal)
        analytics_text = await self._run_role("Analytics", analytics_instructions, startup_goal)

        marketing_assets = _extract_json(marketing_text) or [marketing_text] if marketing_text else []
        growth_assets = _extract_json(growth_text) or [growth_text] if growth_text else []

        agent, agent_payload = await self.agent_generator.generate_agent(
            db=db,
            goal=startup_goal,
            owner_id=owner_id,
            workspace_id=workspace_id,
            category="founder"
        )

        workflow = await self.workflow_service.generate_workflow(
            db,
            startup_goal,
            owner_id=owner_id
        )

        listing = self.publisher.publish_agent(
            db,
            agent_id=agent.id,
            seller_id=owner_id,
            price=29.0,
            category="founder",
            auto=True,
            capabilities=agent_payload.get("capabilities"),
            pricing_tier="growth"
        )

        product_bundle = None
        try:
            product_bundle = await self.product_generator.generate_product(
                db=db,
                goal=startup_goal,
                owner_id=owner_id,
                workspace_id=workspace_id
            )
        except Exception as exc:
            logger.warning("Founder product generator failed: %s", exc)

        demand = self.product_generator.analyze_marketplace_demand(db)
        analytics_snapshot = AnalyticsService.task_completion(db)

        agents_created = [{"id": agent.id, "name": agent.name}]
        workflows_created = [{"id": workflow.id, "name": workflow.name}]
        if product_bundle:
            product_agent = product_bundle.get("agent")
            product_workflow = product_bundle.get("workflow")
            if product_agent and product_agent.get("id") != agent.id:
                agents_created.append(product_agent)
            if product_workflow and product_workflow.get("id") != workflow.id:
                workflows_created.append(product_workflow)

        return {
            "strategy": strategy,
            "product_plan": product_plan,
            "agents_created": agents_created,
            "workflows_created": workflows_created,
            "marketing_assets": marketing_assets if isinstance(marketing_assets, list) else [str(marketing_assets)],
            "growth_assets": growth_assets if isinstance(growth_assets, list) else [str(growth_assets)],
            "marketplace_listing_id": listing.id if listing else None,
            "product_bundle": product_bundle,
            "demand_insights": demand,
            "analytics_insights": {
                "snapshot": analytics_snapshot,
                "recommendations": analytics_text
            }
        }
