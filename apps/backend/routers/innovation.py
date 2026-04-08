from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from database_production import get_db
from models import Goal, Simulation, DigitalTwinProfile, Opportunity, EthicalLog, User
from services.innovation_service import GoalService, SimulationService, DigitalTwinService, DiscoveryService
from pydantic import BaseModel
from datetime import datetime
from security import get_current_user
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/innovation", tags=["innovation"])

# --- Schemas ---
class GoalCreate(BaseModel):
    title: str
    description: str

class SimulationRequest(BaseModel):
    agent_id: int
    scenario: str

class DigitalTwinUpdate(BaseModel):
    preferences: dict

class GoalSchema(BaseModel):
    id: int
    title: str
    status: str
    progress: int
    class Config:
        from_attributes = True

class OpportunitySchema(BaseModel):
    id: int
    title: str
    description: str
    type: str
    confidence_score: float
    source: str
    class Config:
        from_attributes = True

# --- Endpoints ---

@router.post("/goals", response_model=GoalSchema)
async def create_goal(goal: GoalCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return await GoalService.create_goal(db, current_user.id, goal.title, goal.description)

@router.get("/goals", response_model=List[GoalSchema])
def list_goals(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(Goal).filter(Goal.user_id == current_user.id, Goal.parent_id == None).all()

@router.post("/simulations")
async def run_simulation(request: SimulationRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return await SimulationService.run_simulation(db, request.agent_id, request.scenario)

@router.get("/digital-twin")
def get_digital_twin(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Get or create digital twin profile"""
    try:
        profile = db.query(DigitalTwinProfile).filter(DigitalTwinProfile.user_id == current_user.id).first()
        if not profile:
            profile = DigitalTwinProfile(user_id=current_user.id)
            db.add(profile)
            db.commit()
            db.refresh(profile)
        return {
            "id": profile.id,
            "user_id": profile.user_id,
            "preferences": profile.preferences or {},
            "behavior_model": profile.behavior_model or {},
            "proactive_enabled": bool(profile.proactive_enabled),
            "predicted_needs": profile.predicted_needs or [],
            "automated_tasks": profile.automated_tasks or [],
            "last_updated": profile.last_updated.isoformat() if profile.last_updated else None
        }
    except Exception as e:
        logger.error(f"Error getting digital twin profile: {e}", exc_info=True)
        # Return a default profile instead of crashing
        return {
            "id": None,
            "user_id": current_user.id,
            "preferences": {},
            "behavior_model": {},
            "proactive_enabled": False,
            "predicted_needs": [],
            "automated_tasks": [],
            "last_updated": None
        }

@router.put("/digital-twin")
async def update_digital_twin(update: DigitalTwinUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    try:
        profile = await DigitalTwinService.update_profile(db, current_user.id, update.preferences)
        return {
            "id": profile.id,
            "user_id": profile.user_id,
            "preferences": profile.preferences or {},
            "behavior_model": profile.behavior_model or {},
            "proactive_enabled": bool(profile.proactive_enabled),
            "predicted_needs": profile.predicted_needs or [],
            "automated_tasks": profile.automated_tasks or [],
            "last_updated": profile.last_updated.isoformat() if profile.last_updated else None
        }
    except Exception as e:
        logger.error(f"Error updating digital twin profile: {e}", exc_info=True)
        return {
            "success": False,
            "error": "Failed to update digital twin profile",
            "code": 500
        }

@router.get("/opportunities", response_model=List[OpportunitySchema])
async def get_opportunities(refresh: bool = False, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if refresh:
        return await DiscoveryService.scan_opportunities(db)
    return db.query(Opportunity).all()
