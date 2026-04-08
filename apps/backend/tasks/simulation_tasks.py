import logging
from typing import Any, Dict

from celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="tasks.simulation_tasks.run_simulation")
def run_simulation_task(payload: Dict[str, Any]):
    logger.info("Simulation queued: %s", payload.get("simulation_id"))
    return {"status": "queued", "simulation_id": payload.get("simulation_id")}
