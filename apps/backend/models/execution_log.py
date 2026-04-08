from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base


class ExecutionLog(Base):
    __tablename__ = "execution_logs"

    id = Column(Integer, primary_key=True, index=True)
    execution_id = Column(Integer, ForeignKey("executions.id"), nullable=True)
    agent_id = Column(Integer, ForeignKey("agents.id"), nullable=False)
    prompt_version_id = Column(Integer, ForeignKey("prompt_versions.id"), nullable=True)
    step = Column(Integer, default=0)
    phase = Column(String, nullable=False)
    message = Column(String, nullable=False)
    payload = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    execution = relationship("Execution")
    agent = relationship("Agent")
