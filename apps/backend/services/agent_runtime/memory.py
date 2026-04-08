from typing import Optional, List
import logging

logger = logging.getLogger(__name__)


class MemoryProvider:
    def retrieve_context(self, db, agent_id: int, query: Optional[str], limit: int = 5) -> str:
        raise NotImplementedError

    def store_memory(self, db, agent_id: int, query: Optional[str], outcome: str, success_rating: int = 8) -> None:
        raise NotImplementedError


class DefaultMemoryProvider(MemoryProvider):
    def retrieve_context(self, db, agent_id: int, query: Optional[str], limit: int = 5) -> str:
        if not query:
            return ""
        try:
            sections: List[str] = []

            # Conversation memory (recent runs)
            try:
                from models import AgentRun
                recent = (
                    db.query(AgentRun)
                    .filter(AgentRun.agent_id == agent_id)
                    .order_by(AgentRun.created_at.desc())
                    .limit(limit)
                    .all()
                )
                if recent:
                    sections.append(
                        "Conversation Memory:\n"
                        + "\n".join(
                            [f"- {r.input_prompt[:80]} -> {r.output_response[:120]}..." for r in recent]
                        )
                    )
            except Exception:
                pass

            # Vector knowledge base
            try:
                from services.vector_memory import VectorMemoryService
                memories = VectorMemoryService.search(db, agent_id, query, limit=limit)
                if memories:
                    sections.append(
                        "Vector Memory:\n"
                        + "\n".join([f"- {m.content[:140]}..." for m in memories])
                    )
            except Exception:
                pass

            # Long-term memory from intelligence service
            try:
                from services.intelligence_service import MemoryService
                long_term = MemoryService.recall_memories(db, agent_id, query) or []
                if long_term:
                    sections.append(
                        "Long-term Memory:\n"
                        + "\n".join(
                            [f"- Input: {m.query} -> Result: {m.outcome[:120]}..." for m in long_term[:limit]]
                        )
                    )
            except Exception:
                pass

            # Knowledge base (shared knowledge)
            try:
                from models import SharedKnowledge
                knowledge = (
                    db.query(SharedKnowledge)
                    .filter(SharedKnowledge.topic.ilike(f"%{query}%"))
                    .order_by(SharedKnowledge.reinforcement_score.desc())
                    .limit(limit)
                    .all()
                )
                if knowledge:
                    sections.append(
                        "Knowledge Base:\n"
                        + "\n".join([f"- {k.topic}: {k.content[:140]}..." for k in knowledge])
                    )
            except Exception:
                pass

            return "\n\n".join(sections)
        except Exception as exc:
            logger.warning("Memory retrieval failed: %s", exc)
            return ""

    def store_memory(self, db, agent_id: int, query: Optional[str], outcome: str, success_rating: int = 8) -> None:
        if not query:
            return
        try:
            try:
                from services.vector_memory import VectorMemoryService
                VectorMemoryService.store_memory(db, agent_id, content=f"{query}\n{outcome}")
            except Exception:
                pass

            from services.intelligence_service import MemoryService
            MemoryService.store_memory(
                db,
                agent_id,
                query=query,
                decision="Executed via agent runtime",
                outcome=outcome,
                success_rating=success_rating
            )
        except Exception as exc:
            logger.warning("Memory store failed: %s", exc)
