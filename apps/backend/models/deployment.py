from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, Float
from sqlalchemy.orm import relationship
from database import Base
from datetime import datetime

class Feedback(Base):
    __tablename__ = "feedbacks"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    type = Column(String)  # "bug", "feature", "rating"
    message = Column(Text, nullable=True)
    rating = Column(Integer, nullable=True)  # 1-5
    created_at = Column(DateTime, default=datetime.utcnow)

class MemoryShard(Base):
    __tablename__ = "memory_shards"
    id = Column(Integer, primary_key=True, index=True)
    shard_id = Column(String, unique=True) # e.g. "shard-001"
    region = Column(String) # e.g. "us-east-1"
    status = Column(String) # active, rebalancing
    capacity_usage = Column(Float, default=0.0) # Percentage
    last_heartbeat = Column(DateTime, default=datetime.utcnow)

class ProjectTemplate(Base):
    __tablename__ = "project_templates"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    description = Column(String)
    category = Column(String)  # "business", "developer", "creator"
    config = Column(Text)  # JSON string of agent definitions
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
