from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # New Role Support
    role = Column(String, default="user") # user, admin, developer
    is_active = Column(String, default=True)
    referral_code = Column(String, unique=True, index=True, nullable=True) # The code they share

    # Multi-tenant
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=True, index=True)
    
    # Monetization Fields
    executions_this_month = Column(Integer, default=0)
    tokens_used_this_month = Column(Integer, default=0)
    subscription_tier = Column(String, default="free")  # free, pro, enterprise
    subscription_status = Column(String, default="active")  # active, canceled, trialing
    
    # Email Verification
    is_email_verified = Column(String, default=False)  # Must verify email before executing agents
    email_verification_code = Column(String, nullable=True)  # 6-digit code
    email_verification_expires_at = Column(DateTime, nullable=True)  # Code expires in 15 minutes
    
    # Password Reset
    password_reset_token = Column(String, nullable=True)  # Hashed token
    password_reset_expires_at = Column(DateTime, nullable=True)  # Token expires in 30 minutes

    agents = relationship("Agent", back_populates="owner")
    workflows = relationship("Workflow", back_populates="owner")
    refresh_tokens = relationship("RefreshToken", back_populates="user")
    organization = relationship(
        "Organization",
        back_populates="users",
        foreign_keys=[organization_id],
    )
