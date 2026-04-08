
"""
Agent Feedback Model - Stores user feedback on agent executions
Allows agents to learn from user ratings and improve over time
"""
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Text, Float
from sqlalchemy.orm import relationship
from database import Base
from datetime import datetime


class AgentFeedback(Base):
    """
    Model for storing user feedback on agent executions

    Fields:
        id: Unique identifier for the feedback
        agent_run_id: Reference to the agent run being rated
        rating: User rating (1-5 stars)
        feedback_text: Detailed feedback from user
        created_at: Timestamp when feedback was submitted
    """
    __tablename__ = "agent_feedback"

    id = Column(Integer, primary_key=True, index=True)
    agent_run_id = Column(Integer, ForeignKey("agent_runs.id"), nullable=False, index=True)
    rating = Column(Integer, nullable=False)  # 1-5 stars
    feedback_text = Column(Text, nullable=True)  # Optional detailed feedback
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationship to AgentRun
    agent_run = relationship("AgentRun", back_populates="feedback")
