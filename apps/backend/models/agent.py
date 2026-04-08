from sqlalchemy import Column, Integer, String, ForeignKey, JSON, Boolean, DateTime, Float
from sqlalchemy.orm import relationship
from database import Base
from datetime import datetime

class Agent(Base):
    __tablename__ = "agents"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    description = Column(String)
    config = Column(JSON, nullable=True)
    owner_id = Column(Integer, ForeignKey("users.id"))

    owner = relationship("User", back_populates="agents")
    executions = relationship("Execution", back_populates="agent")
    
    is_published = Column(Boolean, default=False)
    tags = Column(String, nullable=True)  # JSON string or comma-separated
    category = Column(String, nullable=True)
    version = Column(String, default="1.0.0")
    
    workspace_id = Column(Integer, ForeignKey("workspaces.id"), nullable=True)
    
    # Scaling & Execution
    edge_enabled = Column(Boolean, default=False)
    resource_priority = Column(String, default="normal") # low, normal, high, critical
    
    # Learning & Performance Metrics
    performance_rating = Column(Float, default=0.0) # 0.0 to 10.0
    execution_count = Column(Integer, default=0)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Role and Skills
    role = Column(String, nullable=True)  # Agent's role (e.g., "Marketing", "Support")
    skills = Column(JSON, nullable=True)  # List of skills as JSON array
    
    # AI Provider Configuration
    ai_provider = Column(String, nullable=True, default="local")  # AI provider: openai, anthropic, gemini, local
    model_name = Column(String, nullable=True, default="qwen2.5:7b-instruct")  # Model name
    temperature = Column(Float, nullable=True, default=0.7)  # Temperature for generation

    workspace = relationship("Workspace", back_populates="agents")
    memories = relationship("AgentMemory", back_populates="agent")
    reviews = relationship("AgentReview", back_populates="agent")
    versions = relationship("AgentVersion", back_populates="agent")
    runs = relationship("AgentRun", back_populates="agent")
    prompt_versions = relationship("PromptVersion", back_populates="agent")

class AgentVersion(Base):
    __tablename__ = "agent_versions"

    id = Column(Integer, primary_key=True, index=True)
    agent_id = Column(Integer, ForeignKey("agents.id"))
    version = Column(String)
    config = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    description = Column(String, nullable=True) # Changelog

    agent = relationship("Agent", back_populates="versions")
