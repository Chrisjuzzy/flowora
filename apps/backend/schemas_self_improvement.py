
"""
Self-Improvement Schemas - Pydantic models for agent learning and feedback
"""
from pydantic import BaseModel, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime


class AgentFeedbackCreate(BaseModel):
    """Schema for creating agent feedback"""
    agent_run_id: int
    rating: int  # 1-5 stars
    feedback_text: Optional[str] = None

    model_config = ConfigDict(arbitrary_types_allowed=True)


class AgentFeedbackResponse(BaseModel):
    """Schema for agent feedback response"""
    id: int
    agent_run_id: int
    rating: int
    feedback_text: Optional[str]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AgentMemoryResponse(BaseModel):
    """Schema for agent memory response"""
    id: int
    agent_id: int
    query: str
    decision: str
    outcome: str
    success_rating: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AgentLearningProgress(BaseModel):
    """Schema for agent learning progress"""
    agent_id: int
    total_runs: int
    avg_feedback_rating: Optional[float]
    feedback_count: int
    memory_count: int
    avg_success_rating: Optional[float]

    model_config = ConfigDict(from_attributes=True)


class AgentMemoryListResponse(BaseModel):
    """Schema for agent memory list"""
    memories: List[AgentMemoryResponse]
    total: int
    page: int
    page_size: int

    model_config = ConfigDict(from_attributes=True)


class AgentRunListResponse(BaseModel):
    """Schema for agent run list"""
    runs: List[Dict[str, Any]]
    total: int
    page: int
    page_size: int

    model_config = ConfigDict(from_attributes=True)
