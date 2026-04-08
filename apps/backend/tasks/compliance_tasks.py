import logging
from typing import Any, Dict

from celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="tasks.compliance_tasks.run_compliance_scan")
def run_compliance_scan_task(payload: Dict[str, Any]):
    target = payload.get("target")
    scan_type = payload.get("scan_type", "quick")
    logger.info("Compliance scan queued for %s (%s)", target, scan_type)
    return {"status": "queued", "target": target, "scan_type": scan_type}
