from sqlalchemy import Column, Integer, String, Boolean, DateTime, JSON, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base


class AgentTemplate(Base):
    __tablename__ = "agent_templates"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    description = Column(String, nullable=True)
    category = Column(String, index=True, nullable=True)
    tags = Column(String, nullable=True)
    version = Column(String, default="1.0.0", index=True)
    base_config = Column(JSON, nullable=True)
    tools = Column(JSON, nullable=True)
    is_active = Column(Boolean, default=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    creator = relationship("User", backref="agent_templates")
    stats = relationship("AgentTemplateStats", back_populates="template", uselist=False, cascade="all, delete-orphan")


class AgentTemplateStats(Base):
    __tablename__ = "agent_template_stats"

    id = Column(Integer, primary_key=True, index=True)
    template_id = Column(Integer, ForeignKey("agent_templates.id"), unique=True, index=True, nullable=False)
    install_count = Column(Integer, default=0)
    share_count = Column(Integer, default=0)
    last_installed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    template = relationship("AgentTemplate", back_populates="stats")
