from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, Text, Float
from sqlalchemy.orm import relationship
from database import Base
from datetime import datetime

class AgentMemory(Base):
    __tablename__ = "agent_memories"
    
    id = Column(Integer, primary_key=True, index=True)
    agent_id = Column(Integer, ForeignKey("agents.id"))
    query = Column(String, index=True)  # The input that triggered this memory
    decision = Column(Text)             # The agent's reasoning
    outcome = Column(Text)              # The actual result
    success_rating = Column(Integer)    # 1-10 rating of success
    embedding_id = Column(String, nullable=True) # Placeholder for vector DB ID
    created_at = Column(DateTime, default=datetime.utcnow)
    
    agent = relationship("Agent", back_populates="memories")

class ReflectionLog(Base):
    __tablename__ = "reflection_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    execution_id = Column(Integer, ForeignKey("executions.id"))
    agent_id = Column(Integer, ForeignKey("agents.id"))
    confidence_score = Column(Float)    # 0.0 to 1.0
    critique = Column(Text)             # Self-criticism
    suggestions = Column(Text)          # How to improve next time
    is_flagged = Column(Boolean, default=False) # Flagged for low confidence
    created_at = Column(DateTime, default=datetime.utcnow)
    
    execution = relationship("Execution")
    agent = relationship("Agent")

class SharedKnowledge(Base):
    __tablename__ = "shared_knowledge"
    
    id = Column(Integer, primary_key=True, index=True)
    source_agent_id = Column(Integer, ForeignKey("agents.id"))
    topic = Column(String, index=True)
    content = Column(Text)
    category = Column(String)           # e.g., "coding_pattern", "marketing_tip"
    usage_count = Column(Integer, default=0)
    reinforcement_score = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    source_agent = relationship("Agent")

class SkillEvolution(Base):
    __tablename__ = "skill_evolution"
    
    id = Column(Integer, primary_key=True, index=True)
    agent_id = Column(Integer, ForeignKey("agents.id"))
    issue_detected = Column(String)     # "High error rate", "Low confidence"
    proposed_prompt = Column(Text)      # New suggested system prompt
    status = Column(String, default="pending") # pending, approved, rejected
    created_at = Column(DateTime, default=datetime.utcnow)
    
    agent = relationship("Agent")

# --- Collaboration Models ---

class AgentMessage(Base):
    __tablename__ = "agent_messages"
    
    id = Column(Integer, primary_key=True, index=True)
    sender_agent_id = Column(Integer, ForeignKey("agents.id"))
    receiver_agent_id = Column(Integer, ForeignKey("agents.id"))
    content = Column(Text)               # Free-form text or JSON string
    status = Column(String, default="delivered")  # delivered, read, failed
    created_at = Column(DateTime, default=datetime.utcnow)
    
    sender = relationship("Agent", foreign_keys=[sender_agent_id])
    receiver = relationship("Agent", foreign_keys=[receiver_agent_id])

class DelegatedTask(Base):
    __tablename__ = "delegated_tasks"
    
    id = Column(Integer, primary_key=True, index=True)
    parent_agent_id = Column(Integer, ForeignKey("agents.id"))
    child_agent_id = Column(Integer, ForeignKey("agents.id"))
    goal = Column(Text)                  # High-level objective
    input_payload = Column(Text, nullable=True)   # Task-specific input
    status = Column(String, default="pending")    # pending, in_progress, completed, failed
    priority = Column(Integer, default=5)         # 1 (high) - 10 (low)
    result = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    
    parent_agent = relationship("Agent", foreign_keys=[parent_agent_id])
    child_agent = relationship("Agent", foreign_keys=[child_agent_id])

class WorkspaceMemory(Base):
    __tablename__ = "workspace_memory"
    
    id = Column(Integer, primary_key=True, index=True)
    workspace_id = Column(Integer, ForeignKey("workspaces.id"))
    key = Column(String, index=True)                 # topic/key
    value = Column(Text)                              # content/value
    author_agent_id = Column(Integer, ForeignKey("agents.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    workspace = relationship("Workspace")
    author_agent = relationship("Agent")

class FailurePattern(Base):
    __tablename__ = "failure_patterns"
    
    id = Column(Integer, primary_key=True, index=True)
    agent_id = Column(Integer, ForeignKey("agents.id"))
    pattern_signature = Column(String, index=True) # Hash or keyword signature
    description = Column(String)                   # "Timeout in API calls", "Hallucination"
    frequency = Column(Integer, default=1)
    last_occurrence = Column(DateTime, default=datetime.utcnow)
    severity = Column(String, default="medium")    # low, medium, high
    
    agent = relationship("Agent")
