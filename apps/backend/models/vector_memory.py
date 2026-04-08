from sqlalchemy import Column, Integer, String, DateTime, JSON, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base
import os

try:
    from pgvector.sqlalchemy import Vector  # type: ignore
except Exception:
    Vector = None

DB_URL = os.getenv("DATABASE_URL", "")
PGVECTOR_ENABLED = os.getenv("USE_PGVECTOR", "true").strip().lower() in {"1", "true", "yes", "on"}
USE_PGVECTOR = bool(Vector) and PGVECTOR_ENABLED and DB_URL.startswith("postgres")
EMBEDDING_TYPE = Vector(1536) if USE_PGVECTOR else JSON


class VectorMemory(Base):
    __tablename__ = "vector_memories"

    id = Column(Integer, primary_key=True, index=True)
    agent_id = Column(Integer, ForeignKey("agents.id"), index=True)
    content = Column(String)
    embedding = Column(EMBEDDING_TYPE)
    metadata_json = Column("metadata", JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    agent = relationship("Agent", backref="vector_memories")
