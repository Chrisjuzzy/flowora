import logging
from typing import Any, Dict

from celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="tasks.ethics_tasks.run_ethics_audit")
def run_ethics_audit_task(payload: Dict[str, Any]):
    logger.info("Ethics audit queued: %s", payload.get("system_name"))
    return {"status": "queued", "system": payload.get("system_name")}
