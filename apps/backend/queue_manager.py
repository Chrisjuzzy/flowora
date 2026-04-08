"""
Queue Manager

Provides a unified interface for background task execution using Celery (if available)
or FastAPI BackgroundTasks as a fallback.
"""
from __future__ import annotations

from typing import Any, Callable, Dict, Optional
import logging

from config_production import settings
from services.queue_protection import enqueue_task

logger = logging.getLogger(__name__)

try:
    from celery import Celery  # type: ignore
    _celery_available = True
except Exception:
    Celery = None
    _celery_available = False


celery_app = None
if _celery_available:
    try:
        celery_app = Celery(
            "ai_agent_builder",
            broker=settings.CELERY_BROKER_URL,
            backend=settings.CELERY_RESULT_BACKEND
        )
        celery_app.conf.update(
            task_track_started=settings.CELERY_TASK_TRACK_STARTED,
            task_time_limit=settings.CELERY_TASK_TIME_LIMIT,
            task_soft_time_limit=settings.CELERY_TASK_SOFT_TIME_LIMIT,
            worker_prefetch_multiplier=settings.CELERY_WORKER_PREFETCH_MULTIPLIER,
            worker_concurrency=settings.CELERY_WORKER_CONCURRENCY,
            task_acks_late=settings.CELERY_ACKS_LATE,
            task_reject_on_worker_lost=settings.CELERY_REJECT_ON_WORKER_LOST
        )
        logger.info("Celery configured for background tasks")
    except Exception as exc:
        logger.warning("Celery init failed, falling back to BackgroundTasks: %s", exc)
        celery_app = None


class QueueManager:
    def __init__(self):
        self.celery_app = celery_app

    def enqueue(
        self,
        task_name: str,
        payload: Dict[str, Any],
        background_tasks: Optional[Any] = None,
        fallback_handler: Optional[Callable[[Dict[str, Any]], Any]] = None
    ):
        if self.celery_app:
            try:
                return enqueue_task(task_name, kwargs=payload)
            except Exception as exc:
                logger.warning("Celery enqueue failed: %s", exc)

        if background_tasks and fallback_handler:
            background_tasks.add_task(fallback_handler, payload)
            return {"status": "queued", "queue": "background_tasks", "task": task_name}

        if fallback_handler:
            # Synchronous fallback
            return fallback_handler(payload)

        return {"status": "skipped", "reason": "no_queue_backend"}


queue_manager = QueueManager()
