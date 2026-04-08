from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Text, Float, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base


class PromptVersion(Base):
    __tablename__ = "prompt_versions"

    id = Column(Integer, primary_key=True, index=True)
    agent_id = Column(Integer, ForeignKey("agents.id"), nullable=False, index=True)
    prompt_text = Column(Text, nullable=False)
    success_rate = Column(Float, default=0.0)
    total_runs = Column(Integer, default=0)
    avg_latency_ms = Column(Float, default=0.0)
    is_active = Column(Boolean, default=False)
    source = Column(String, default="auto")  # auto, manual, seed
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_evaluated_at = Column(DateTime, nullable=True)

    agent = relationship("Agent", back_populates="prompt_versions")
