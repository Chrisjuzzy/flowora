from sqlalchemy import Column, Integer, String, DateTime, JSON, Text
from datetime import datetime
from database import Base


class FounderRun(Base):
    __tablename__ = "founder_runs"

    id = Column(Integer, primary_key=True, index=True)
    run_type = Column(String, default="weekly", index=True)
    status = Column(String, default="completed", index=True)
    trend_snapshot = Column(JSON, nullable=True)
    automation_ideas = Column(JSON, nullable=True)
    agents_created = Column(JSON, nullable=True)
    workflows_created = Column(JSON, nullable=True)
    templates_published = Column(JSON, nullable=True)
    listings_published = Column(JSON, nullable=True)
    summary = Column(JSON, nullable=True)
    error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
