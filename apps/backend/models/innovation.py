from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, Float, Text, JSON, Enum
from sqlalchemy.orm import relationship
from database import Base
from datetime import datetime
import enum

class GoalStatus(str, enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"

class Goal(Base):
    __tablename__ = "goals"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    title = Column(String, index=True)
    description = Column(Text, nullable=True)
    status = Column(String, default=GoalStatus.PENDING)
    progress = Column(Integer, default=0) # 0-100
    parent_id = Column(Integer, ForeignKey("goals.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    due_date = Column(DateTime, nullable=True)
    
    user = relationship("User")
    subgoals = relationship("Goal", backref="parent_goal", remote_side=[id])

class Simulation(Base):
    __tablename__ = "simulations"
    
    id = Column(Integer, primary_key=True, index=True)
    agent_id = Column(Integer, ForeignKey("agents.id"))
    scenario = Column(Text)
    predicted_outcome = Column(Text, nullable=True)
    score = Column(Integer, nullable=True) # 0-100
    created_at = Column(DateTime, default=datetime.utcnow)
    
    agent = relationship("Agent")

class DigitalTwinProfile(Base):
    __tablename__ = "digital_twin_profiles"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)
    preferences = Column(JSON, default={})
    behavior_model = Column(JSON, default={}) # Learned patterns
    proactive_enabled = Column(Boolean, default=False)
    predicted_needs = Column(JSON, default=[]) # List of predicted future needs
    automated_tasks = Column(JSON, default=[]) # Log of tasks automated ahead of time
    last_updated = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User")

class BoardAdvisor(Base):
    __tablename__ = "board_advisors"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    agent_id = Column(Integer, ForeignKey("agents.id"))
    role = Column(String) # Legal, Marketing, etc.
    
    user = relationship("User")
    agent = relationship("Agent")

class EvolutionExperiment(Base):
    __tablename__ = "evolution_experiments"
    
    id = Column(Integer, primary_key=True, index=True)
    agent_id = Column(Integer, ForeignKey("agents.id"))
    original_prompt = Column(Text)
    mutated_prompt = Column(Text)
    status = Column(String, default="running") # running, completed
    performance_delta = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    agent = relationship("Agent")

class IntelligenceGraphNode(Base):
    __tablename__ = "intelligence_graph_nodes"
    
    id = Column(Integer, primary_key=True, index=True)
    agent_id = Column(Integer, ForeignKey("agents.id"))
    knowledge_id = Column(Integer, ForeignKey("shared_knowledge.id"))
    connection_strength = Column(Float, default=1.0)
    
    agent = relationship("Agent")
    knowledge = relationship("SharedKnowledge")

class Opportunity(Base):
    __tablename__ = "opportunities"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    description = Column(Text)
    type = Column(String) # market_trend, business_idea, automation_gap
    confidence_score = Column(Float) # 0.0 - 1.0
    source = Column(String, nullable=True)
    status = Column(String, default="new") # new, dismissed, saved
    created_at = Column(DateTime, default=datetime.utcnow)

class EthicalLog(Base):
    __tablename__ = "ethical_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    execution_id = Column(Integer, ForeignKey("executions.id"), nullable=True)
    check_type = Column(String) # toxicity, bias, sensitive_data
    passed = Column(Boolean)
    details = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    execution = relationship("Execution")
