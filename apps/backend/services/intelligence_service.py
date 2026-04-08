import asyncio
import json
import logging
import time
from typing import List, Dict, Any, Optional

from sqlalchemy import or_
from sqlalchemy.orm import Session

from config_production import settings
from database_production import get_db_context
from models import AgentMemory, ReflectionLog, SharedKnowledge, SkillEvolution, AgentMessage, DelegatedTask, WorkspaceMemory
from services.ai_provider_service import AIProviderFactory

logger = logging.getLogger(__name__)
runtime_ai_service = AIProviderFactory.get_provider(settings.DEFAULT_AI_PROVIDER)

# --- Memory Service ---
class MemoryService:
    @staticmethod
    def store_memory(db: Session, agent_id: int, query: str, decision: str, outcome: str, success_rating: int):
        memory = AgentMemory(
            agent_id=agent_id,
            query=query,
            decision=decision,
            outcome=outcome,
            success_rating=success_rating
        )
        db.add(memory)
        db.commit()
        db.refresh(memory)
        return memory

    @staticmethod
    def recall_memories(db: Session, agent_id: int, query: str, limit: int = 3) -> List[AgentMemory]:
        # Keyword-based search (simulating vector retrieval)
        # 1. Exact match attempt
        # 2. Split words and check for partial matches in query OR outcome
        
        words = query.split()
        if not words:
            return []
            
        filters = [AgentMemory.agent_id == agent_id]
        
        # Build OR conditions for keywords
        keyword_conditions = []
        for word in words:
            if len(word) > 3: # Skip small words
                keyword_conditions.append(AgentMemory.query.ilike(f"%{word}%"))
                keyword_conditions.append(AgentMemory.outcome.ilike(f"%{word}%"))
        
        if keyword_conditions:
            filters.append(or_(*keyword_conditions))
        else:
            # Fallback if all words short
            filters.append(AgentMemory.query.ilike(f"%{query}%"))

        memories = db.query(AgentMemory).filter(*filters).order_by(AgentMemory.created_at.desc()).limit(limit).all()
        return memories

# --- Reflection Service ---
class ReflectionService:
    _pending_tasks: set[asyncio.Task] = set()
    _semaphore: Optional[asyncio.Semaphore] = None
    _last_log_times: dict[str, float] = {}

    @classmethod
    def _get_semaphore(cls) -> asyncio.Semaphore:
        if cls._semaphore is None:
            cls._semaphore = asyncio.Semaphore(max(1, settings.REFLECTION_MAX_CONCURRENCY))
        return cls._semaphore

    @staticmethod
    def _clip_text(value: Optional[str], limit: int) -> str:
        if not value:
            return ""
        text_value = str(value)
        if len(text_value) <= limit:
            return text_value
        return f"{text_value[:limit]}\n...[truncated]"

    @classmethod
    def _log_with_cooldown(cls, key: str, level: str, message: str, *args) -> None:
        cooldown = max(0, settings.REFLECTION_LOG_COOLDOWN_SECONDS)
        now = time.monotonic()
        previous = cls._last_log_times.get(key)
        if previous is not None and cooldown and now - previous < cooldown:
            return
        cls._last_log_times[key] = now
        getattr(logger, level)(message, *args)

    @classmethod
    def _prune_tasks(cls) -> None:
        cls._pending_tasks = {task for task in cls._pending_tasks if not task.done()}

    @classmethod
    def _track_task(cls, task: asyncio.Task) -> None:
        cls._pending_tasks.add(task)

        def _on_done(done_task: asyncio.Task) -> None:
            cls._pending_tasks.discard(done_task)
            try:
                done_task.result()
            except asyncio.CancelledError:
                return
            except Exception as exc:
                cls._log_with_cooldown(
                    "reflection_background_failure",
                    "info",
                    "Background reflection skipped after non-critical error: %s",
                    exc,
                )

        task.add_done_callback(_on_done)

    @classmethod
    def schedule_reflection(
        cls,
        agent_id: int,
        execution_id: int,
        input_data: str,
        result: str,
    ) -> bool:
        if not settings.ENABLE_REFLECTION:
            return False
        if (settings.REFLECTION_MODE or "background").lower() == "off":
            return False
        if not input_data or not result:
            return False

        cls._prune_tasks()
        if len(cls._pending_tasks) >= settings.REFLECTION_MAX_PENDING_TASKS:
            cls._log_with_cooldown(
                "reflection_queue_full",
                "info",
                "Skipping reflection because the background queue is full (%s pending tasks).",
                len(cls._pending_tasks),
            )
            return False

        try:
            task = asyncio.create_task(
                cls._run_background_reflection(
                    agent_id=agent_id,
                    execution_id=execution_id,
                    input_data=input_data,
                    result=result,
                ),
                name=f"reflection-{execution_id}",
            )
        except RuntimeError:
            cls._log_with_cooldown(
                "reflection_scheduler_unavailable",
                "info",
                "Skipping reflection because no event loop is available.",
            )
            return False

        cls._track_task(task)
        return True

    @classmethod
    async def _run_background_reflection(
        cls,
        agent_id: int,
        execution_id: int,
        input_data: str,
        result: str,
    ) -> None:
        async with cls._get_semaphore():
            try:
                await asyncio.wait_for(
                    cls._reflect_with_fresh_session(
                        agent_id=agent_id,
                        execution_id=execution_id,
                        input_data=input_data,
                        result=result,
                    ),
                    timeout=max(1, settings.REFLECTION_TIMEOUT_SECONDS),
                )
            except asyncio.TimeoutError:
                cls._log_with_cooldown(
                    "reflection_timeout",
                    "info",
                    "Background reflection skipped after %ss timeout.",
                    settings.REFLECTION_TIMEOUT_SECONDS,
                )
            except Exception as exc:
                cls._log_with_cooldown(
                    "reflection_failure",
                    "info",
                    "Background reflection skipped after non-critical error: %s",
                    exc,
                )

    @classmethod
    async def _reflect_with_fresh_session(
        cls,
        agent_id: int,
        execution_id: int,
        input_data: str,
        result: str,
    ) -> Optional[ReflectionLog]:
        with get_db_context() as db:
            return await cls.reflect_on_execution(
                db=db,
                agent_id=agent_id,
                execution_id=execution_id,
                input_data=input_data,
                result=result,
            )

    @classmethod
    def _build_prompt(cls, input_data: str, result: str) -> str:
        clipped_input = cls._clip_text(input_data, settings.REFLECTION_MAX_INPUT_CHARS)
        clipped_result = cls._clip_text(result, settings.REFLECTION_MAX_RESULT_CHARS)
        return (
            "Review this AI agent execution and respond with strict JSON only.\n"
            'Required keys: "confidence_score", "critique", "suggestions", "is_flagged".\n'
            '"confidence_score" must be a float between 0.0 and 1.0.\n'
            '"is_flagged" must be true only for clearly low-quality, unsafe, or failed results.\n'
            f"Input:\n{clipped_input}\n\n"
            f"Result:\n{clipped_result}\n"
        )

    @staticmethod
    def _parse_response(text_resp: str) -> tuple[float, str, str, bool]:
        confidence = 0.8
        critique = "Standard execution."
        suggestions = "None."
        is_flagged = False

        if "{" in text_resp and "}" in text_resp:
            try:
                start = text_resp.find("{")
                end = text_resp.rfind("}") + 1
                data = json.loads(text_resp[start:end])
                confidence = float(data.get("confidence_score", confidence))
                critique = str(data.get("critique", critique))
                suggestions = str(data.get("suggestions", suggestions))
                is_flagged = bool(data.get("is_flagged", is_flagged))
                return confidence, critique, suggestions, is_flagged
            except Exception:
                pass

        if text_resp.strip():
            critique = text_resp.strip()
        return confidence, critique, suggestions, is_flagged

    @classmethod
    async def reflect_on_execution(
        cls,
        db: Session,
        agent_id: int,
        execution_id: int,
        input_data: str,
        result: str,
    ) -> Optional[ReflectionLog]:
        prompt = cls._build_prompt(input_data, result)

        try:
            ai_response = await runtime_ai_service.generate_with_metadata(
                prompt,
                model=settings.DEFAULT_AI_MODEL,
            )
            text_resp = ai_response.get("text", "")
            confidence, critique, suggestions, is_flagged = cls._parse_response(text_resp)

            log = ReflectionLog(
                execution_id=execution_id,
                agent_id=agent_id,
                confidence_score=confidence,
                critique=critique,
                suggestions=suggestions,
                is_flagged=is_flagged,
            )
            db.add(log)
            db.commit()
            db.refresh(log)

            if is_flagged or confidence < 0.6:
                EvolutionService.schedule_improvement(agent_id, critique)

            return log
        except Exception:
            db.rollback()
            raise

# --- Knowledge Service ---
class KnowledgeService:
    @staticmethod
    def share_insight(db: Session, agent_id: int, topic: str, content: str, category: str):
        # Check duplicates
        existing = db.query(SharedKnowledge).filter(
            SharedKnowledge.topic == topic, 
            SharedKnowledge.category == category
        ).first()
        
        if existing:
            return existing
            
        item = SharedKnowledge(
            source_agent_id=agent_id,
            topic=topic,
            content=content,
            category=category
        )
        db.add(item)
        db.commit()
        return item

    @staticmethod
    def get_relevant_knowledge(db: Session, topic_query: str) -> List[SharedKnowledge]:
        return db.query(SharedKnowledge).filter(
            SharedKnowledge.topic.ilike(f"%{topic_query}%")
        ).order_by(SharedKnowledge.reinforcement_score.desc()).all()

# --- Evolution Service ---
class EvolutionService:
    @classmethod
    def schedule_improvement(cls, agent_id: int, issue: str) -> bool:
        if not settings.ENABLE_REFLECTION_EVOLUTION:
            return False
        if not issue:
            return False

        try:
            task = asyncio.create_task(
                cls._run_background_improvement(agent_id, issue[:500]),
                name=f"reflection-evolution-{agent_id}",
            )
        except RuntimeError:
            return False

        ReflectionService._track_task(task)
        return True

    @classmethod
    async def _run_background_improvement(cls, agent_id: int, issue: str) -> None:
        try:
            await asyncio.wait_for(
                cls._propose_improvement_with_fresh_session(agent_id, issue),
                timeout=max(1, settings.REFLECTION_EVOLUTION_TIMEOUT_SECONDS),
            )
        except asyncio.TimeoutError:
            ReflectionService._log_with_cooldown(
                "reflection_evolution_timeout",
                "info",
                "Deferred reflection evolution skipped after %ss timeout.",
                settings.REFLECTION_EVOLUTION_TIMEOUT_SECONDS,
            )
        except Exception as exc:
            ReflectionService._log_with_cooldown(
                "reflection_evolution_failure",
                "info",
                "Deferred reflection evolution skipped after non-critical error: %s",
                exc,
            )

    @classmethod
    async def _propose_improvement_with_fresh_session(cls, agent_id: int, issue: str) -> None:
        with get_db_context() as db:
            await cls.propose_improvement(db, agent_id, issue)

    @staticmethod
    async def propose_improvement(db: Session, agent_id: int, issue: str):
        # Generate a new prompt proposal
        prompt = f"""
        An AI agent is struggling with: {issue}.
        Suggest an improved system prompt or configuration to handle this better.
        """
        response = await runtime_ai_service.generate_with_metadata(
            prompt,
            model=settings.DEFAULT_AI_MODEL
        )
        
        evolution = SkillEvolution(
            agent_id=agent_id,
            issue_detected=issue[:200], # Truncate for DB
            proposed_prompt=response["text"],
            status="pending"
        )
        db.add(evolution)
        db.commit()

# --- Collaboration Services ---
class MessagingDelegationService:
    @staticmethod
    def send_message(db: Session, sender_agent_id: int, receiver_agent_id: int, content: str) -> AgentMessage:
        msg = AgentMessage(
            sender_agent_id=sender_agent_id,
            receiver_agent_id=receiver_agent_id,
            content=content,
            status="delivered"
        )
        db.add(msg)
        db.commit()
        db.refresh(msg)
        return msg
    
    @staticmethod
    def list_messages(db: Session, agent_id: int, peer_id: Optional[int] = None, limit: int = 50) -> List[AgentMessage]:
        q = db.query(AgentMessage).filter(
            or_(AgentMessage.sender_agent_id == agent_id, AgentMessage.receiver_agent_id == agent_id)
        ).order_by(AgentMessage.created_at.desc())
        if peer_id:
            q = q.filter(
                or_(
                    AgentMessage.sender_agent_id == peer_id,
                    AgentMessage.receiver_agent_id == peer_id
                )
            )
        return q.limit(limit).all()
    
    @staticmethod
    def delegate_task(db: Session, parent_agent_id: int, child_agent_id: int, goal: str, input_payload: Optional[str] = None, priority: int = 5) -> DelegatedTask:
        task = DelegatedTask(
            parent_agent_id=parent_agent_id,
            child_agent_id=child_agent_id,
            goal=goal,
            input_payload=input_payload or "",
            priority=priority,
            status="pending"
        )
        db.add(task)
        db.commit()
        db.refresh(task)
        return task
    
    @staticmethod
    def update_task_status(db: Session, task_id: int, status: str, result: Optional[str] = None) -> DelegatedTask:
        task = db.query(DelegatedTask).filter(DelegatedTask.id == task_id).first()
        if not task:
            raise ValueError("Delegated task not found")
        task.status = status
        if result is not None:
            task.result = result
        if status in ("completed", "failed"):
            from datetime import datetime
            task.completed_at = datetime.utcnow()
        db.commit()
        db.refresh(task)
        return task

class WorkspaceMemoryService:
    @staticmethod
    def write_memory(db: Session, workspace_id: int, key: str, value: str, author_agent_id: Optional[int] = None) -> WorkspaceMemory:
        item = WorkspaceMemory(
            workspace_id=workspace_id,
            key=key,
            value=value,
            author_agent_id=author_agent_id
        )
        db.add(item)
        db.commit()
        db.refresh(item)
        return item
    
    @staticmethod
    def read_memory(db: Session, workspace_id: int, key: Optional[str] = None, limit: int = 20) -> List[WorkspaceMemory]:
        q = db.query(WorkspaceMemory).filter(WorkspaceMemory.workspace_id == workspace_id).order_by(WorkspaceMemory.created_at.desc())
        if key:
            q = q.filter(WorkspaceMemory.key == key)
        return q.limit(limit).all()

class ConflictResolver:
    @staticmethod
    def resolve(candidates: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Resolve conflicting candidate outputs.
        Strategy:
        - Prefer higher 'confidence' if provided.
        - Otherwise, prefer longer informative text (as heuristic).
        """
        if not candidates:
            return {"text": "", "agent_id": None, "reason": "no_candidates"}
        
        # Filter out empty texts
        valid = [c for c in candidates if c.get("text")]
        if not valid:
            return {"text": "", "agent_id": None, "reason": "empty_candidates"}
        
        # If any provides confidence, use max confidence
        with_conf = [c for c in valid if isinstance(c.get("confidence"), (int, float))]
        if with_conf:
            best = max(with_conf, key=lambda c: c.get("confidence", 0))
            best["reason"] = "max_confidence"
            return best
        
        # Fallback: choose the longest text
        best = max(valid, key=lambda c: len(c.get("text", "")))
        best["reason"] = "longest_text"
        return best
