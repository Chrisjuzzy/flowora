from sqlalchemy.orm import Session
from services.agent_runtime.runtime import default_runtime

async def run_agent(db: Session, agent_id: int, input_data: str = None, simulation_mode: bool = False, user_id: int = None):
    """
    Delegate to the new Agent Runtime pipeline.
    """
    return await default_runtime.execute(
        db=db,
        agent_id=agent_id,
        input_data=input_data,
        simulation_mode=simulation_mode,
        user_id=user_id
    )
