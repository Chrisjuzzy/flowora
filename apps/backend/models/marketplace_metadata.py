from sqlalchemy import Column, Integer, String, JSON, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base


class MarketplaceListingMetadata(Base):
    __tablename__ = "marketplace_listing_metadata"

    id = Column(Integer, primary_key=True, index=True)
    listing_id = Column(Integer, ForeignKey("marketplace_listings.id"), index=True)
    capabilities = Column(JSON, nullable=True)
    pricing_tier = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    listing = relationship("MarketplaceListing", backref="metadata_records")
