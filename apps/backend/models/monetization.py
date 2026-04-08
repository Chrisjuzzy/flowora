from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    Numeric,
    String,
)
from sqlalchemy.orm import relationship
from database import Base
from datetime import datetime

class Wallet(Base):
    __tablename__ = "wallets"
    __table_args__ = (
        CheckConstraint("balance >= 0", name="ck_wallets_balance_non_negative"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)
    balance = Column(Numeric(18, 6), default=0.0, nullable=False)  # In USD or Credits
    currency = Column(String, default="USD", nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    user = relationship("User", backref="wallet")
    transactions = relationship("Transaction", back_populates="wallet")

class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    wallet_id = Column(Integer, ForeignKey("wallets.id"))
    amount = Column(Numeric(18, 6), nullable=False)  # Positive for credit, negative for debit
    type = Column(String, nullable=False)  # "recharge", "execution_cost", "marketplace_purchase", "marketplace_sale"
    description = Column(String)
    reference_id = Column(String, nullable=True) # ID of related entity (execution_id, payment_id)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    wallet = relationship("Wallet", back_populates="transactions")


class WalletCharge(Base):
    __tablename__ = "wallet_charges"

    id = Column(Integer, primary_key=True, index=True)
    wallet_id = Column(Integer, ForeignKey("wallets.id"))
    amount = Column(Numeric(18, 6), nullable=False)
    currency = Column(String, default="USD", nullable=False)
    status = Column(String, default="pending", nullable=False)  # pending, succeeded, failed
    provider = Column(String, default="mock", nullable=False)
    provider_reference = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    wallet = relationship("Wallet", backref="charges")

class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    amount = Column(Numeric(18, 6), nullable=False)
    status = Column(String) # paid, pending, failed
    stripe_invoice_id = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", backref="invoices")

class MarketplaceListing(Base):
    __tablename__ = "marketplace_listings"

    id = Column(Integer, primary_key=True, index=True)
    agent_id = Column(Integer, ForeignKey("agents.id"), unique=True)
    resource_type = Column(String, default="agent", index=True)  # agent, template, workflow, plugin
    resource_id = Column(Integer, nullable=True, index=True)
    seller_id = Column(Integer, ForeignKey("users.id"))
    price = Column(Numeric(18, 6))
    category = Column(String, index=True, nullable=True)
    is_active = Column(Boolean, default=True)
    downloads = Column(Integer, default=0)
    rating = Column(Float, default=0.0, index=True)
    version = Column(String, default="1.0.0", index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    agent = relationship("Agent")
    seller = relationship("User", backref="listings")


class MarketplaceReview(Base):
    __tablename__ = "marketplace_reviews"

    id = Column(Integer, primary_key=True, index=True)
    listing_id = Column(Integer, ForeignKey("marketplace_listings.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    rating = Column(Integer)
    comment = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    listing = relationship("MarketplaceListing", backref="reviews")
    user = relationship("User", backref="marketplace_reviews")

class Purchase(Base):
    __tablename__ = "purchases"

    id = Column(Integer, primary_key=True, index=True)
    listing_id = Column(Integer, ForeignKey("marketplace_listings.id"))
    buyer_id = Column(Integer, ForeignKey("users.id"))
    amount = Column(Numeric(18, 6), nullable=False)
    commission = Column(Numeric(18, 6), nullable=False) # Platform fee
    seller_revenue = Column(Numeric(18, 6), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    listing = relationship("MarketplaceListing")
    buyer = relationship("User", backref="purchases")


class CreditTransaction(Base):
    """
    Tracks credit transactions (usage and purchases).
    
    Different from Transaction which tracks wallet money.
    This tracks the credit-based system per tier.
    """
    __tablename__ = "credit_transactions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    amount = Column(Integer)  # Credits added/deducted
    type = Column(String)  # "purchase", "usage", "refund", "monthly_grant"
    description = Column(String)
    agent_type = Column(String, nullable=True)  # Agent that consumed credits (if type="usage")
    reference_id = Column(String, nullable=True)  # Execution ID, transaction ID, etc.
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    user = relationship("User", backref="credit_transactions")


class UserRevenueTracking(Base):
    """
    Tracks revenue reported by users as generated through platform usage.
    
    Users can report revenue their agents/workflows generated.
    This helps build credibility and case studies.
    """
    __tablename__ = "user_revenue_tracking"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    reported_revenue = Column(Float)  # Revenue amount
    source_agent = Column(String, nullable=True)  # Agent type that generated it
    description = Column(String, nullable=True)  # How revenue was generated
    verified = Column(Boolean, default=False)  # Admin verification status
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    user = relationship("User", backref="revenue_reports")


class MarketplaceAgent(Base):
    """
    System agents available in the marketplace.
    
    Represents production-ready AI agents that users can execute.
    Each execution costs credits (amount varies by agent).
    """
    __tablename__ = "marketplace_agents"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)  # Display name
    slug = Column(String, unique=True, index=True)  # URL-friendly identifier
    description = Column(String)  # Long description
    short_tagline = Column(String, nullable=True)  # Short marketing tagline
    category = Column(String, index=True)  # Category (Lead Generation, Marketing, etc.)
    credit_cost = Column(Integer, default=1)  # Credits per execution
    is_active = Column(Boolean, default=True, index=True)
    is_system_agent = Column(Boolean, default=True)  # System vs. third-party
    creator_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # Future: third-party creators
    
    estimated_output_time = Column(Integer, nullable=True)  # Seconds
    popularity_score = Column(Integer, default=50)  # 1-100 rating
    execution_count = Column(Integer, default=0)  # Total times executed
    
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    creator = relationship("User", backref="created_agents", foreign_keys=[creator_user_id])
