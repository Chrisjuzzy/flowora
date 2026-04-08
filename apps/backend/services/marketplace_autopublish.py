import logging
from typing import Optional

from sqlalchemy.orm import Session

from models import Agent, MarketplaceListing, MarketplaceListingMetadata

logger = logging.getLogger(__name__)


class MarketplaceAutopublishService:
    def publish_agent(
        self,
        db: Session,
        agent_id: int,
        seller_id: Optional[int],
        price: float,
        category: Optional[str] = None,
        auto: bool = False,
        capabilities: Optional[list] = None,
        pricing_tier: Optional[str] = None
    ) -> MarketplaceListing:
        agent = db.query(Agent).filter(Agent.id == agent_id).first()
        if not agent:
            raise ValueError("Agent not found")

        existing = db.query(MarketplaceListing).filter(MarketplaceListing.agent_id == agent_id).first()
        if existing:
            if auto:
                existing.price = price
                existing.category = category or existing.category
                existing.is_active = True
                db.commit()
                db.refresh(existing)
                self._upsert_metadata(db, existing.id, capabilities, pricing_tier)
            return existing

        listing = MarketplaceListing(
            agent_id=agent_id,
            seller_id=seller_id,
            price=price,
            category=category or agent.category,
            is_active=True
        )
        db.add(listing)
        agent.is_published = True
        db.commit()
        db.refresh(listing)
        self._upsert_metadata(db, listing.id, capabilities, pricing_tier)
        return listing

    def _upsert_metadata(
        self,
        db: Session,
        listing_id: int,
        capabilities: Optional[list],
        pricing_tier: Optional[str]
    ) -> None:
        if capabilities is None and pricing_tier is None:
            return
        record = (
            db.query(MarketplaceListingMetadata)
            .filter(MarketplaceListingMetadata.listing_id == listing_id)
            .first()
        )
        if record:
            if capabilities is not None:
                record.capabilities = capabilities
            if pricing_tier is not None:
                record.pricing_tier = pricing_tier
        else:
            db.add(
                MarketplaceListingMetadata(
                    listing_id=listing_id,
                    capabilities=capabilities,
                    pricing_tier=pricing_tier
                )
            )
        db.commit()
