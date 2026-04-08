from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, JSON
from sqlalchemy.orm import relationship
from database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    is_active = Column(Boolean, default=True)

    agents = relationship("Agent", back_populates="owner")

class Agent(Base):
    __tablename__ = "agents"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    agent_type = Column(String, nullable=True, index=True)  # Type identifier (e.g., "lead_generator", "social_content")
    description = Column(String, nullable=True)
    config = Column(JSON, nullable=True) # To store agent-specific configuration (e.g., model, prompt)
    is_active = Column(Boolean, default=True)
    owner_id = Column(Integer, ForeignKey("users.id"))

    owner = relationship("User", back_populates="agents")
