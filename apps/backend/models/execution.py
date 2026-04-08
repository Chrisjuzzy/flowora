from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from database import Base
from datetime import datetime

class Execution(Base):
    __tablename__ = "executions"

    id = Column(Integer, primary_key=True, index=True)
    agent_id = Column(Integer, ForeignKey("agents.id"))
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True) # Who executed it
    prompt_version_id = Column(Integer, ForeignKey("prompt_versions.id"), nullable=True)
    status = Column(String)
    result = Column(String)
    token_usage = Column(Integer, default=0)
    execution_time_ms = Column(Integer, default=0)
    cost_estimate = Column(String, default="0.0")  # Store as string for precision or float
    timestamp = Column(DateTime, default=datetime.utcnow)

    agent = relationship("Agent", back_populates="executions")
