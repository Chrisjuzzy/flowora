
"""
Celery Application - Background task processing for Flowora
Handles agent executions, long-running workflows, and scheduled tasks
"""
from celery import Celery
from celery.signals import task_failure
from celery.schedules import crontab
from config_production import settings
import logging

logger = logging.getLogger(__name__)

# Create Celery app
celery_app = Celery(
    'flowora',
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        'tasks.agent_tasks',
        'tasks.workflow_tasks',
        'tasks.scheduled_tasks',
        'tasks.swarm_tasks',
        'tasks.compliance_tasks',
        'tasks.ethics_tasks',
        'tasks.simulation_tasks',
        'tasks.optimization_tasks'
    ]
)

# Celery configuration
celery_app.conf.update(
    # Task settings
    task_track_started=settings.CELERY_TASK_TRACK_STARTED,
    task_time_limit=settings.CELERY_TASK_TIME_LIMIT,
    task_soft_time_limit=settings.CELERY_TASK_SOFT_TIME_LIMIT,
    task_acks_late=settings.CELERY_ACKS_LATE,
    task_reject_on_worker_lost=settings.CELERY_REJECT_ON_WORKER_LOST,

    # Worker settings
    worker_prefetch_multiplier=settings.CELERY_WORKER_PREFETCH_MULTIPLIER,
    worker_concurrency=settings.CELERY_WORKER_CONCURRENCY,
    worker_max_tasks_per_child=settings.CELERY_MAX_TASKS_PER_CHILD,
    worker_max_memory_per_child=int(settings.CELERY_MAX_MEMORY_PER_CHILD_MB * 1024),

    # Result settings
    result_expires=3600,  # Results expire after 1 hour
    result_extended=True,

    # Task routing
    task_routes={
        'tasks.agent_tasks.execute_agent': {'queue': 'agent_executions'},
        'tasks.workflow_tasks.run_workflow': {'queue': 'workflows'},
        'tasks.optimization_tasks.optimize_agent': {'queue': 'optimization'},
        'tasks.scheduled_tasks.*': {'queue': 'scheduled'},
        'tasks.swarm_tasks.*': {'queue': 'swarm'},
        'tasks.compliance_tasks.*': {'queue': 'compliance'},
        'tasks.ethics_tasks.*': {'queue': 'ethics'},
        'tasks.simulation_tasks.*': {'queue': 'simulation'}
    },

    # Task serialization
    task_serializer='json',
    result_serializer='json',
    accept_content=['json'],

    # Timezone
    timezone='UTC',
    enable_utc=True,

    # Error handling
    task_annotations={
        'tasks.agent_tasks.execute_agent': {'rate_limit': '5/m'},
    },

    # Retry settings
    task_default_retry_delay=60,
    task_max_retries=3,
    task_default_retry_policy='exponential',
)

# Configure periodic tasks
celery_app.conf.beat_schedule = {
    # Cleanup old executions every hour
    'cleanup-old-executions': {
        'task': 'tasks.scheduled_tasks.cleanup_old_executions',
        'schedule': crontab(minute=0),  # Every hour
    },

    # Update agent performance metrics every 6 hours
    'update-agent-metrics': {
        'task': 'tasks.scheduled_tasks.update_agent_metrics',
        'schedule': crontab(minute=0, hour='*/6'),  # Every 6 hours
    },

    # Continuous agent learning every 6 hours
    'continuous-agent-learning': {
        'task': 'tasks.scheduled_tasks.continuous_agent_learning',
        'schedule': crontab(minute=0, hour='*/6'),
    },

    # Weekly founder mode automation (Mondays at 00:00 UTC)
    'weekly-founder-mode': {
        'task': 'tasks.scheduled_tasks.weekly_founder_mode',
        'schedule': crontab(minute=0, hour=0, day_of_week='mon'),
    },

    # Send daily usage reports at midnight
    'daily-usage-report': {
        'task': 'tasks.scheduled_tasks.send_daily_usage_report',
        'schedule': crontab(minute=0, hour=0),  # Daily at midnight
    },

    # Worker memory monitoring every 5 minutes
    'monitor-worker-memory': {
        'task': 'tasks.scheduled_tasks.monitor_worker_memory',
        'schedule': crontab(minute='*/5'),
    },
}

logger.info("Celery application configured successfully")


@task_failure.connect
def handle_task_failure(sender=None, task_id=None, exception=None, args=None, kwargs=None, einfo=None, **extras):
    try:
        from services.queue_protection import record_dead_letter
        record_dead_letter({
            "task_id": task_id,
            "task_name": getattr(sender, "name", None),
            "exception": str(exception),
            "args": args,
            "kwargs": kwargs
        })
    except Exception as exc:
        logger.error("Dead letter handler failed: %s", exc, exc_info=True)
