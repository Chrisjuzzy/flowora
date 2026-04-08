import logging
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session
from sqlalchemy import func

from models import MarketplaceListing, Purchase
from services.agent_generator import AgentGenerator
from services.autonomous_workflows import WorkflowAutogenService
from services.marketplace_autopublish import MarketplaceAutopublishService

logger = logging.getLogger(__name__)


class AIProductGenerator:
    def __init__(self, provider_name: str = "openai") -> None:
        self.provider_name = provider_name
        self.agent_generator = AgentGenerator(provider_name=provider_name)
        self.workflow_service = WorkflowAutogenService(provider_name=provider_name)
        self.publisher = MarketplaceAutopublishService()

    def analyze_marketplace_demand(self, db: Session) -> Dict[str, Any]:
        listings = db.query(
            MarketplaceListing.category,
            func.count(MarketplaceListing.id).label("count")
        ).group_by(MarketplaceListing.category).all()
        purchases = db.query(
            MarketplaceListing.category,
            func.count(Purchase.id).label("purchases")
        ).join(MarketplaceListing, MarketplaceListing.id == Purchase.listing_id).group_by(
            MarketplaceListing.category
        ).all()

        listing_map = {c or "general": count for c, count in listings}
        purchase_map = {c or "general": count for c, count in purchases}

        best_category = "general"
        best_score = -1
        for category, count in listing_map.items():
            demand = purchase_map.get(category, 0)
            supply = count or 1
            score = demand / supply
            if score > best_score:
                best_score = score
                best_category = category

        return {
            "recommended_category": best_category,
            "demand_score": round(best_score, 2),
            "listing_counts": listing_map,
            "purchase_counts": purchase_map
        }

    async def generate_product(
        self,
        db: Session,
        goal: str,
        owner_id: Optional[int] = None,
        workspace_id: Optional[int] = None
    ) -> Dict[str, Any]:
        demand = self.analyze_marketplace_demand(db)
        category = demand.get("recommended_category")

        agent, agent_payload = await self.agent_generator.generate_agent(
            db=db,
            goal=goal,
            owner_id=owner_id,
            workspace_id=workspace_id,
            category=category
        )

        workflow = await self.workflow_service.generate_workflow(db, goal, owner_id=owner_id)

        listing = self.publisher.publish_agent(
            db,
            agent_id=agent.id,
            seller_id=owner_id,
            price=19.0,
            category=category,
            auto=True,
            capabilities=agent_payload.get("capabilities"),
            pricing_tier="premium"
        )

        return {
            "status": "generated",
            "demand": demand,
            "agent": {"id": agent.id, "name": agent.name},
            "workflow": {"id": workflow.id, "name": workflow.name},
            "listing": {"id": listing.id, "price": listing.price}
        }
