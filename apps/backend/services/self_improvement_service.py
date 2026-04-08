
"""
Self-Improvement Service - Enables agents to learn from past executions
Handles memory loading, memory writing, and improvement logic
"""
import logging
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from models import Agent, AgentRun, AgentFeedback, AgentMemory
from services.redis_service import get_cache
from services.encryption import encryption_service

logger = logging.getLogger(__name__)


class SelfImprovementService:
    """Service for managing agent self-improvement through memory and feedback"""

    @staticmethod
    def load_agent_memory(db: Session, agent_id: int, current_prompt: str) -> str:
        """
        Load previous memory related to the agent and current prompt

        Args:
            db: Database session
            agent_id: ID of the agent
            current_prompt: Current user prompt

        Returns:
            Memory context string to append to prompt
        """
        try:
            # Check cache first
            cache = get_cache()
            cache_key = f"agent_memory:{agent_id}:{hash(current_prompt)}"
            cached_memory = cache.get(cache_key) if cache else None
            if cached_memory:
                logger.info(f"Using cached memory for agent {agent_id}")
                return cached_memory

            # Query recent memories (last 30 days)
            thirty_days_ago = datetime.utcnow() - timedelta(days=30)
            memories = db.query(AgentMemory).filter(
                AgentMemory.agent_id == agent_id,
                AgentMemory.created_at >= thirty_days_ago
            ).order_by(AgentMemory.created_at.desc()).limit(10).all()

            if not memories:
                logger.info(f"No memories found for agent {agent_id}")
                return ""

            # Build memory context
            memory_context = "\n\nRelevant Past Experiences:\n"
            for i, memory in enumerate(memories, 1):
                memory_context += f"{i}. Query: {memory.query}\n"
                memory_context += f"   Decision: {memory.decision[:100]}...\n"
                memory_context += f"   Outcome: {memory.outcome[:100]}...\n"
                memory_context += f"   Success Rating: {memory.success_rating}/10\n\n"

            # Cache the memory context
            if cache:
                cache.set(cache_key, memory_context, ttl=3600)  # Cache for 1 hour

            logger.info(f"Loaded {len(memories)} memories for agent {agent_id}")
            return memory_context

        except Exception as e:
            logger.error(f"Error loading agent memory: {e}")
            return ""

    @staticmethod
    def write_agent_memory(db: Session, agent_id: int, input_prompt: str, 
                         output_response: str, execution_time: int) -> bool:
        """
        Store useful outputs into agent memory

        Args:
            db: Database session
            agent_id: ID of the agent
            input_prompt: The input provided to the agent
            output_response: The response from the agent
            execution_time: Time taken to execute (in milliseconds)

        Returns:
            True if successful, False otherwise
        """
        try:
            # Determine if this execution was successful
            success_rating = 8  # Default rating

            # Check if execution was fast and produced output
            if execution_time < 5000 and len(output_response) > 50:
                success_rating = 9
            elif execution_time < 10000 and len(output_response) > 20:
                success_rating = 7

            # Create memory entry
            memory = AgentMemory(
                agent_id=agent_id,
                query=input_prompt,
                decision=f"Generated response based on: {input_prompt[:100]}",
                outcome=output_response,
                success_rating=success_rating,
                created_at=datetime.utcnow()
            )

            db.add(memory)
            db.commit()

            # Clear related cache
            cache = get_cache()
            cache_key = f"agent_memory:{agent_id}:{hash(input_prompt)}"
            if cache:
                cache.delete(cache_key)

            logger.info(f"Stored memory for agent {agent_id} with rating {success_rating}")
            return True

        except Exception as e:
            logger.error(f"Error writing agent memory: {e}")
            return False

    @staticmethod
    def get_improvement_context(db: Session, agent_id: int, user_prompt: str) -> str:
        """
        Combine agent instructions, previous memory, and new user prompt
        This allows the agent to improve responses over time

        Args:
            db: Database session
            agent_id: ID of the agent
            user_prompt: New user prompt

        Returns:
            Enhanced prompt with memory context
        """
        try:
            # Get agent
            agent = db.query(Agent).filter(Agent.id == agent_id).first()
            if not agent:
                logger.error(f"Agent {agent_id} not found")
                return user_prompt

            # Get agent instructions
            instructions = agent.description or ""
            if agent.config:
                try:
                    agent_config = encryption_service.decrypt_data(agent.config)
                    if isinstance(agent_config, dict):
                        instructions = agent_config.get("instructions", agent_config.get("system_prompt", ""))
                except Exception as e:
                    logger.warning(f"Failed to decrypt agent config: {e}")

            # Load memory context
            memory_context = SelfImprovementService.load_agent_memory(
                db, agent_id, user_prompt
            )

            # Combine all components
            enhanced_prompt = f"{instructions}\n\n"
            if memory_context:
                enhanced_prompt += f"{memory_context}\n\n"
            enhanced_prompt += f"Current Task:\n{user_prompt}"

            logger.info(f"Created improvement context for agent {agent_id}")
            return enhanced_prompt

        except Exception as e:
            logger.error(f"Error creating improvement context: {e}")
            return user_prompt

    @staticmethod
    def process_feedback(db: Session, agent_run_id: int, rating: int, 
                     feedback_text: Optional[str] = None) -> bool:
        """
        Process user feedback on agent execution
        Updates agent memory based on feedback

        Args:
            db: Database session
            agent_run_id: ID of the agent run
            rating: User rating (1-5)
            feedback_text: Optional detailed feedback

        Returns:
            True if successful, False otherwise
        """
        try:
            # Get agent run
            agent_run = db.query(AgentRun).filter(
                AgentRun.id == agent_run_id
            ).first()

            if not agent_run:
                logger.error(f"Agent run {agent_run_id} not found")
                return False

            # Store feedback
            feedback = AgentFeedback(
                agent_run_id=agent_run_id,
                rating=rating,
                feedback_text=feedback_text,
                created_at=datetime.utcnow()
            )

            db.add(feedback)

            # Update memory success rating based on feedback
            if rating >= 4:  # Good feedback
                # Find related memory and update success rating
                memory = db.query(AgentMemory).filter(
                    AgentMemory.agent_id == agent_run.agent_id,
                    AgentMemory.query == agent_run.input_prompt
                ).first()

                if memory:
                    memory.success_rating = min(10, memory.success_rating + 2)
                    db.commit()
                    logger.info(f"Updated memory success rating to {memory.success_rating}")

            db.commit()

            # Clear cache for this agent
            cache = get_cache()
            cache_key = f"agent_memory:{agent_run.agent_id}:{hash(agent_run.input_prompt)}"
            if cache:
                cache.delete(cache_key)

            logger.info(f"Processed feedback for agent run {agent_run_id}")
            return True

        except Exception as e:
            logger.error(f"Error processing feedback: {e}")
            return False

    @staticmethod
    def get_agent_learning_progress(db: Session, agent_id: int) -> Dict[str, Any]:
        """
        Get learning progress statistics for an agent

        Args:
            db: Database session
            agent_id: ID of the agent

        Returns:
            Dict with learning statistics
        """
        try:
            # Get total runs
            total_runs = db.query(AgentRun).filter(
                AgentRun.agent_id == agent_id
            ).count()

            # Get average feedback rating
            avg_feedback = db.query(AgentFeedback).join(
                AgentRun, AgentFeedback.agent_run_id == AgentRun.id
            ).filter(AgentRun.agent_id == agent_id).all()

            if avg_feedback:
                avg_rating = sum(f.rating for f in avg_feedback) / len(avg_feedback)
            else:
                avg_rating = None

            # Get memory count
            memory_count = db.query(AgentMemory).filter(
                AgentMemory.agent_id == agent_id
            ).count()

            # Get average success rating
            avg_success = db.query(AgentMemory).filter(
                AgentMemory.agent_id == agent_id
            ).all()

            if avg_success:
                avg_success_rating = sum(m.success_rating for m in avg_success) / len(avg_success)
            else:
                avg_success_rating = None

            return {
                "agent_id": agent_id,
                "total_runs": total_runs,
                "avg_feedback_rating": avg_rating,
                "feedback_count": len(avg_feedback) if avg_feedback else 0,
                "memory_count": memory_count,
                "avg_success_rating": avg_success_rating
            }

        except Exception as e:
            logger.error(f"Error getting learning progress: {e}")
            return {
                "agent_id": agent_id,
                "error": str(e)
            }


# Global instance
self_improvement_service = SelfImprovementService()
