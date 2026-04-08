from typing import Any, Dict, List, Optional
import math
import logging

from sqlalchemy.orm import Session

from models.vector_memory import VectorMemory
from services.vector_memory.embeddings import embed_text

logger = logging.getLogger(__name__)


def _cosine_similarity(a: List[float], b: List[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a)) or 1.0
    norm_b = math.sqrt(sum(y * y for y in b)) or 1.0
    return dot / (norm_a * norm_b)


class VectorMemoryService:
    @staticmethod
    def store_memory(
        db: Session,
        agent_id: int,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> VectorMemory:
        embedding = embed_text(content)
        memory = VectorMemory(
            agent_id=agent_id,
            content=content,
            embedding=embedding,
            metadata_json=metadata or {}
        )
        db.add(memory)
        db.commit()
        db.refresh(memory)
        return memory

    @staticmethod
    def search(
        db: Session,
        agent_id: int,
        query: str,
        limit: int = 5
    ) -> List[VectorMemory]:
        if not query:
            return []
        query_embedding = embed_text(query)
        try:
            # Use pgvector distance if available
            if hasattr(VectorMemory.embedding, "cosine_distance"):
                return (
                    db.query(VectorMemory)
                    .filter(VectorMemory.agent_id == agent_id)
                    .order_by(VectorMemory.embedding.cosine_distance(query_embedding))
                    .limit(limit)
                    .all()
                )
        except Exception:
            pass

        memories = db.query(VectorMemory).filter(VectorMemory.agent_id == agent_id).all()
        scored = [
            (memory, _cosine_similarity(query_embedding, memory.embedding or []))
            for memory in memories
        ]
        scored.sort(key=lambda item: item[1], reverse=True)
        return [memory for memory, _ in scored[:limit]]
