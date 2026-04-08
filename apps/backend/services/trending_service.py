from typing import List, Dict
from sqlalchemy.orm import Session
from sqlalchemy import func

from models import Agent, Execution, Workflow
from models.monetization import MarketplaceListing


class TrendingService:
    @staticmethod
    def top_agents(db: Session, limit: int = 10) -> List[Dict[str, any]]:
        rows = (
            db.query(Agent, func.count(Execution.id).label("exec_count"))
            .join(Execution, Execution.agent_id == Agent.id)
            .group_by(Agent.id)
            .order_by(func.count(Execution.id).desc())
            .limit(limit)
            .all()
        )
        return [
            {
                "agent_id": agent.id,
                "name": agent.name,
                "description": agent.description,
                "executions": count
            }
            for agent, count in rows
        ]

    @staticmethod
    def top_workflows(db: Session, limit: int = 10) -> List[Dict[str, any]]:
        rows = (
            db.query(Workflow)
            .filter(Workflow.is_public == True)
            .order_by(Workflow.clone_count.desc(), Workflow.install_count.desc())
            .limit(limit)
            .all()
        )
        return [
            {
                "workflow_id": wf.id,
                "name": wf.name,
                "description": wf.description,
                "clone_count": wf.clone_count,
                "install_count": wf.install_count
            }
            for wf in rows
        ]

    @staticmethod
    def top_plugins(db: Session, limit: int = 10) -> List[Dict[str, any]]:
        rows = (
            db.query(MarketplaceListing)
            .filter(MarketplaceListing.resource_type == "plugin")
            .order_by(MarketplaceListing.downloads.desc())
            .limit(limit)
            .all()
        )
        return [
            {
                "listing_id": listing.id,
                "resource_id": listing.resource_id,
                "category": listing.category,
                "downloads": listing.downloads
            }
            for listing in rows
        ]
