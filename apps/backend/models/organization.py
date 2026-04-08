from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base


class Organization(Base):
    __tablename__ = "organizations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, unique=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    users = relationship(
        "User",
        back_populates="organization",
        foreign_keys="User.organization_id",
    )
    workspaces = relationship(
        "Workspace",
        back_populates="organization",
        foreign_keys="Workspace.organization_id",
    )
