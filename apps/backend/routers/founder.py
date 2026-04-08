from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session

from database_production import get_db
from security import get_current_user
from services.founder_mode.founder_controller import FounderController

router = APIRouter(prefix="/founder", tags=["founder"])


class FounderRunRequest(BaseModel):
    startup_goal: str
    workspace_id: Optional[int] = None


@router.post("/run")
async def run_founder_mode(
    payload: FounderRunRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    controller = FounderController()
    return await controller.run_founder_mode(
        db=db,
        startup_goal=payload.startup_goal,
        owner_id=current_user.id,
        workspace_id=payload.workspace_id
    )
