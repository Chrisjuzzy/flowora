from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database_production import get_db
from models import AgentRun, Agent

router = APIRouter(prefix="/share", tags=["share"])


@router.get("/{run_id}")
def get_shared_run(run_id: int, db: Session = Depends(get_db)):
    run = db.query(AgentRun).filter(AgentRun.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Shared run not found")

    agent = db.query(Agent).filter(Agent.id == run.agent_id).first()

    return {
        "id": run.id,
        "agent_id": run.agent_id,
        "agent_name": agent.name if agent else "Agent",
        "agent_description": agent.description if agent else None,
        "input_prompt": run.input_prompt,
        "output_response": run.output_response,
        "created_at": run.created_at,
    }
