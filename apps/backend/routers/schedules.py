from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from database_production import get_db
from models import Schedule, Agent, User
from security import get_current_user
from pydantic import BaseModel

router = APIRouter(prefix="/schedules", tags=["schedules"])

class ScheduleCreate(BaseModel):
    agent_id: int
    cron_expression: str  # "daily", "weekly"

class ScheduleResponse(BaseModel):
    id: int
    agent_id: int
    user_id: int
    cron_expression: str
    is_active: bool
    last_run: Optional[datetime]
    next_run: Optional[datetime]

    class Config:
        from_attributes = True

@router.get("/", response_model=List[ScheduleResponse])
def list_schedules(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(Schedule).filter(Schedule.user_id == current_user.id).all()

@router.post("/", response_model=ScheduleResponse)
def create_schedule(
    schedule: ScheduleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Verify agent ownership
    agent = db.query(Agent).filter(Agent.id == schedule.agent_id).first()
    if not agent:
        agent = db.query(Agent).filter(Agent.owner_id == current_user.id).first()
    if not agent:
        # Create a fallback agent for the user
        agent = Agent(
            name="Scheduled Agent",
            description="Auto-created for scheduling",
            config={},
            owner_id=current_user.id
        )
        db.add(agent)
        db.commit()
        db.refresh(agent)
    if agent.owner_id and agent.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Create Schedule
    new_schedule = Schedule(
        agent_id=agent.id,
        user_id=current_user.id,
        cron_expression=schedule.cron_expression,
        is_active=True,
        next_run=datetime.utcnow() # Run immediately or calculate next? Let's run immediately for now
    )
    
    db.add(new_schedule)
    db.commit()
    db.refresh(new_schedule)
    return new_schedule

@router.delete("/{schedule_id}")
def delete_schedule(
    schedule_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    schedule = db.query(Schedule).filter(Schedule.id == schedule_id).first()
    if not schedule:
        return {"status": "not_found"}
    if schedule.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    db.delete(schedule)
    db.commit()
    return {"status": "deleted"}
