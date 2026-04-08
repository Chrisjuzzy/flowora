from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from datetime import datetime
from database import Base


class UsageLog(Base):
    __tablename__ = "usage_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    agent_id = Column(Integer, ForeignKey("agents.id"), nullable=True)
    workflow_id = Column(Integer, ForeignKey("workflows.id"), nullable=True)
    swarm_id = Column(String, nullable=True)
    execution_type = Column(String, index=True)  # agent_run, workflow_run, swarm_run, compliance_scan, ethics_audit, simulation
    compute_time_ms = Column(Integer, default=0)
    tokens_used = Column(Integer, default=0)
    cost = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
