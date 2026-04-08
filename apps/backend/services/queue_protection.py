import json
import logging
from typing import Any, Dict, Optional

from fastapi import HTTPException
from config_production import settings
from services.redis_service import get_redis_client
from utils.prometheus_metrics import record_queue_depth

logger = logging.getLogger(__name__)


def _resolve_queue_name(task_name: str, default_queue: str = "celery") -> str:
    try:
        from celery_app import celery_app
        routes = celery_app.conf.task_routes or {}
        if task_name in routes and isinstance(routes[task_name], dict):
            return routes[task_name].get("queue", default_queue)
        for route_key, route_config in routes.items():
            if not isinstance(route_key, str) or not isinstance(route_config, dict):
                continue
            if route_key.endswith(".*") and task_name.startswith(route_key[:-2]):
                return route_config.get("queue", default_queue)
    except Exception:
        pass
    return default_queue


def _queue_length(queue_name: str) -> int:
    client = get_redis_client()
    if not client:
        return 0
    try:
        depth = int(client.llen(queue_name))
        record_queue_depth(queue_name, depth)
        return depth
    except Exception as exc:
        logger.warning("Queue length check failed for %s: %s", queue_name, exc)
        return 0


def ensure_queue_capacity(queue_name: str, limit: int) -> None:
    depth = _queue_length(queue_name)
    if depth >= limit:
        raise HTTPException(
            status_code=429,
            detail=f"Queue '{queue_name}' is full. Please retry later."
        )


def enqueue_task(task_name: str, args: Optional[list] = None, kwargs: Optional[dict] = None, queue: Optional[str] = None):
    target_queue = queue or _resolve_queue_name(task_name)
    ensure_queue_capacity(target_queue, settings.CELERY_MAX_QUEUE_SIZE)
    from celery_app import celery_app
    return celery_app.send_task(task_name, args=args or [], kwargs=kwargs or {}, queue=target_queue)


def record_dead_letter(payload: Dict[str, Any]) -> None:
    client = get_redis_client()
    if not client:
        logger.warning("Dead letter storage unavailable")
        return
    try:
        client.lpush("dead_letter_queue", json.dumps(payload))
        client.ltrim("dead_letter_queue", 0, 999)
    except Exception as exc:
        logger.error("Failed to persist dead letter payload: %s", exc, exc_info=True)
