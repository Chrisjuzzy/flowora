
"""
Self-Improvement Router - Endpoints for agent learning and feedback
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database_production import get_db
from models import Agent, AgentRun, AgentFeedback, AgentMemory
from schemas_self_improvement import (
    AgentFeedbackCreate, 
    AgentFeedbackResponse,
    AgentMemoryListResponse,
    AgentLearningProgress,
    AgentRunListResponse
)
from services.self_improvement_service import SelfImprovementService
from security import get_current_user
from models import User
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/self-improvement", tags=["self-improvement"])


@router.get("/agents/{agent_id}/memory")
def get_agent_memory(
    agent_id: int,
    page: int = 1,
    page_size: int = 10,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get memory for a specific agent

    Args:
        agent_id: ID of the agent
        page: Page number (default: 1)
        page_size: Number of items per page (default: 10)
        db: Database session
        current_user: Authenticated user

    Returns:
        List of agent memories with pagination
    """
    # Check if agent exists and user has permission
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found"
        )

    # Check permission (owner or admin)
    if agent.owner_id and agent.owner_id != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this agent's memory"
        )

    try:
        # Get memories with pagination
        offset = (page - 1) * page_size
        memories = db.query(AgentMemory).filter(
            AgentMemory.agent_id == agent_id
        ).order_by(AgentMemory.created_at.desc()).offset(offset).limit(page_size).all()

        total = db.query(AgentMemory).filter(
            AgentMemory.agent_id == agent_id
        ).count()

        return AgentMemoryListResponse(
            memories=memories,
            total=total,
            page=page,
            page_size=page_size
        )
    except Exception as e:
        logger.error(f"Error getting agent memory: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve agent memory"
        )


@router.get("/agents/{agent_id}/runs")
def get_agent_runs(
    agent_id: int,
    page: int = 1,
    page_size: int = 10,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get execution history for a specific agent

    Args:
        agent_id: ID of the agent
        page: Page number (default: 1)
        page_size: Number of items per page (default: 10)
        db: Database session
        current_user: Authenticated user

    Returns:
        List of agent runs with pagination
    """
    # Check if agent exists and user has permission
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found"
        )

    # Check permission (owner or admin)
    if agent.owner_id and agent.owner_id != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this agent's runs"
        )

    try:
        # Get runs with pagination
        offset = (page - 1) * page_size
        runs = db.query(AgentRun).filter(
            AgentRun.agent_id == agent_id
        ).order_by(AgentRun.created_at.desc()).offset(offset).limit(page_size).all()

        total = db.query(AgentRun).filter(
            AgentRun.agent_id == agent_id
        ).count()

        # Convert to dict format
        runs_data = [
            {
                "id": run.id,
                "input_prompt": run.input_prompt,
                "output_response": run.output_response,
                "execution_time": run.execution_time,
                "created_at": run.created_at.isoformat(),
                "feedback_count": len(run.feedback) if run.feedback else 0
            }
            for run in runs
        ]

        return AgentRunListResponse(
            runs=runs_data,
            total=total,
            page=page,
            page_size=page_size
        )
    except Exception as e:
        logger.error(f"Error getting agent runs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve agent runs"
        )


@router.post("/agents/{agent_id}/feedback")
def submit_agent_feedback(
    agent_id: int,
    feedback: AgentFeedbackCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Submit feedback for an agent execution

    Args:
        agent_id: ID of the agent
        feedback: Feedback data (agent_run_id, rating, feedback_text)
        db: Database session
        current_user: Authenticated user

    Returns:
        Success message
    """
    # Check if agent exists and user has permission
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found"
        )

    # Check permission (owner or admin)
    if agent.owner_id and agent.owner_id != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to submit feedback for this agent"
        )

    # Validate rating
    if feedback.rating < 1 or feedback.rating > 5:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Rating must be between 1 and 5"
        )

    try:
        agent_run = db.query(AgentRun).filter(AgentRun.id == feedback.agent_run_id).first()
        if not agent_run:
            agent_run = AgentRun(
                agent_id=agent_id,
                input_prompt="Auto-created feedback run",
                output_response="",
                execution_time=0
            )
            db.add(agent_run)
            db.commit()
            db.refresh(agent_run)
            feedback.agent_run_id = agent_run.id

        # Process feedback
        success = SelfImprovementService.process_feedback(
            db=db,
            agent_run_id=feedback.agent_run_id,
            rating=feedback.rating,
            feedback_text=feedback.feedback_text
        )

        return {
            "status": "feedback recorded" if success else "feedback received",
            "agent_id": agent_id,
            "agent_run_id": feedback.agent_run_id,
            "rating": feedback.rating,
            "learning_updated": bool(success)
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error submitting feedback: {e}")
        return {
            "status": "feedback received",
            "agent_id": agent_id,
            "agent_run_id": feedback.agent_run_id,
            "learning_updated": False,
            "error": str(e)
        }


@router.get("/agents/{agent_id}/learning-progress")
def get_learning_progress(
    agent_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get learning progress for a specific agent

    Args:
        agent_id: ID of the agent
        db: Database session
        current_user: Authenticated user

    Returns:
        Learning progress statistics
    """
    # Check if agent exists and user has permission
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found"
        )

    # Check permission (owner or admin)
    if agent.owner_id and agent.owner_id != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this agent's learning progress"
        )

    try:
        # Get learning progress
        progress = SelfImprovementService.get_agent_learning_progress(
            db=db,
            agent_id=agent_id
        )

        return progress
    except Exception as e:
        logger.error(f"Error getting learning progress: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve learning progress"
        )
