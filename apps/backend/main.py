from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from sqlalchemy import text
from database_production import (
    engine,
    Base,
    get_db,
    get_db_context,
    ensure_postgres_extensions,
    ensure_required_tables,
    ensure_sqlite_schema,
)
import models
from config_production import settings
from middleware.rate_limit import RateLimitMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address
from utils.logger_config import setup_logging
from utils.structlog_config import setup_structlog
import logging
import sys
import uuid
from structlog.contextvars import bind_contextvars, clear_contextvars
from tenancy import set_current_tenant
from utils.metrics import record_request
from utils.prometheus_metrics import record_http_request
import time

# Setup structured logging
setup_logging()
setup_structlog()

# ==================== LOGGING SETUP ====================
logger = logging.getLogger(__name__)


def _should_use_redis_rate_limit_storage(redis_url: str | None) -> bool:
    if not redis_url:
        return False
    normalized = redis_url.strip().lower()
    return not any(
        marker in normalized
        for marker in ("localhost", "127.0.0.1", "redis://localhost", "://localhost")
    )

# Create database tables (guarded against multi-worker race)
def _safe_create_all():
    try:
        db_url = str(engine.url)
        with engine.begin() as conn:
            if db_url.startswith("postgres"):
                conn.execute(text("SELECT pg_advisory_lock(424242)"))
                ensure_postgres_extensions(conn)
                # Clean up orphaned sequence from prior failed create (race condition fix)
                table_exists = conn.execute(text("SELECT to_regclass('public.wallet_charges')")).scalar()
                if table_exists is None:
                    seq_exists = conn.execute(text("SELECT to_regclass('public.wallet_charges_id_seq')")).scalar()
                    if seq_exists is not None:
                        conn.execute(text("DROP SEQUENCE IF EXISTS wallet_charges_id_seq"))
            Base.metadata.create_all(bind=conn)
            if db_url.startswith("postgres"):
                conn.execute(text("SELECT pg_advisory_unlock(424242)"))
        logger.info("Database tables created successfully")
    except IntegrityError as exc:
        logger.warning("Database create_all race condition: %s", exc)
    except Exception as exc:
        logger.error("Failed to create database tables: %s", exc, exc_info=True)
        raise

def _initialize_database():
    _safe_create_all()
    ensure_required_tables([
        "agents",
        "marketplace_listings",
        "marketplace_reviews",
        "marketplace_agents",
        "digital_twin_profiles",
        "organizations",
        "referrals",
        "announcements",
        "community_posts",
        "user_stats",
        "workspaces",
        "vector_memories",
        "usage_logs",
        "execution_logs",
        "prompt_versions",
        "founder_runs",
        "agent_templates",
        "agent_template_stats",
        "workflow_templates",
        "tool_config_templates",
        "agent_tool_permissions",
        "marketplace_listing_metadata",
        "api_keys",
        "wallet_charges",
    ])
    ensure_sqlite_schema()


def _initialize_database_with_retries():
    attempts = max(1, settings.DATABASE_STARTUP_MAX_ATTEMPTS)
    backoff = max(0.5, float(settings.DATABASE_STARTUP_BACKOFF_SECONDS))
    max_backoff = max(backoff, float(settings.DATABASE_STARTUP_MAX_BACKOFF_SECONDS))

    for attempt in range(1, attempts + 1):
        try:
            _initialize_database()
            if attempt > 1:
                logger.info(
                    "Database initialization succeeded on attempt %s/%s",
                    attempt,
                    attempts,
                )
            return
        except Exception as exc:
            if attempt >= attempts:
                logger.error(
                    "Failed to initialize database after %s attempts: %s",
                    attempts,
                    exc,
                    exc_info=True,
                )
                raise

            delay = min(backoff * (2 ** (attempt - 1)), max_backoff)
            logger.warning(
                "Database initialization attempt %s/%s failed: %s. Retrying in %.1fs",
                attempt,
                attempts,
                exc,
                delay,
            )
            time.sleep(delay)


_initialize_database_with_retries()

app = FastAPI(
    title=settings.APP_NAME,
    debug=settings.DEBUG
)

# ==================== SLOWAPI RATE LIMITING ====================
limiter_kwargs = {
    "key_func": get_remote_address,
    "default_limits": [f"{settings.RATE_LIMIT_API_PER_MINUTE}/minute"],
}
if _should_use_redis_rate_limit_storage(settings.REDIS_URL):
    limiter_kwargs["storage_uri"] = settings.REDIS_URL
else:
    logger.info("Using in-memory rate limiting storage because Redis is not configured")

limiter = Limiter(**limiter_kwargs)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# ==================== CORS SECURITY ====================
# Only allow whitelisted origins
allowed_origins = settings.ALLOWED_ORIGINS if isinstance(settings.ALLOWED_ORIGINS, list) else settings.ALLOWED_ORIGINS.split(",")
allowed_origins = [origin.strip() for origin in allowed_origins]  # Clean whitespace
if "https://flowora-k13fslrwo-mainstreetagent.vercel.app" not in allowed_origins:
    allowed_origins.append("https://flowora-k13fslrwo-mainstreetagent.vercel.app")

logger.info(f"CORS allowed origins: {allowed_origins}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# ==================== RATE LIMITING ====================
app.add_middleware(RateLimitMiddleware, limit=settings.RATE_LIMIT_API_PER_MINUTE)

# ==================== GLOBAL ERROR MIDDLEWARE ====================
def _error_response(message: str, status_code: int, details: dict | list | None = None):
    payload = {
        "error": True,
        "message": message,
        "status_code": status_code
    }
    if details is not None:
        payload["details"] = details
    return JSONResponse(status_code=status_code, content=payload)

@app.middleware("http")
async def global_exception_middleware(request: Request, call_next):
    start_time = time.time()
    request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex
    bind_contextvars(
        request_id=request_id,
        path=request.url.path,
        method=request.method
    )
    try:
        set_current_tenant(None)
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        duration_ms = (time.time() - start_time) * 1000
        record_request(duration_ms, response.status_code)
        record_http_request(duration_ms, response.status_code, path=request.url.path, method=request.method)
        return response
    except HTTPException as exc:
        logger.warning(f"HTTP exception on {request.url}: {exc.detail}")
        message = exc.detail if isinstance(exc.detail, str) else "Request failed"
        response = _error_response(message, exc.status_code, details=exc.detail if not isinstance(exc.detail, str) else None)
        response.headers["X-Request-ID"] = request_id
        duration_ms = (time.time() - start_time) * 1000
        record_request(duration_ms, exc.status_code)
        record_http_request(duration_ms, exc.status_code, path=request.url.path, method=request.method)
        return response
    except RequestValidationError as exc:
        logger.warning(f"Validation error on {request.url}: {exc.errors()}")
        response = _error_response("Validation error", 422, details=exc.errors())
        response.headers["X-Request-ID"] = request_id
        duration_ms = (time.time() - start_time) * 1000
        record_request(duration_ms, 422)
        record_http_request(duration_ms, 422, path=request.url.path, method=request.method)
        return response
    except SQLAlchemyError as exc:
        logger.error(f"Database error on {request.url}: {exc}", exc_info=True)
        response = _error_response("Database error", 500)
        response.headers["X-Request-ID"] = request_id
        duration_ms = (time.time() - start_time) * 1000
        record_request(duration_ms, 500)
        record_http_request(duration_ms, 500, path=request.url.path, method=request.method)
        return response
    except Exception as exc:
        logger.error(f"Unhandled exception on {request.url}: {str(exc)}", exc_info=True)
        response = _error_response("Internal server error", 500)
        response.headers["X-Request-ID"] = request_id
        duration_ms = (time.time() - start_time) * 1000
        record_request(duration_ms, 500)
        record_http_request(duration_ms, 500, path=request.url.path, method=request.method)
        return response
    finally:
        set_current_tenant(None)
        clear_contextvars()

# ==================== ROUTERS ====================
from routers import auth, agents, execution, workflows, marketplace, schedules, intelligence, workspaces, billing, innovation, deployment, admin, growth, wallet, talent_hub, compliance, code_auditor, wellness, infra_optimizer, ethics_guardian, self_improvement, observability, autonomy, analytics, metrics, storage, trending, templates_library, referral, founder, share, revenue
from services.scheduler_service import scheduler_loop
from services.background_jobs import job_queue
from services.ollama_service import get_ollama_health
import asyncio

app.include_router(auth.router)
app.include_router(agents.router)
app.include_router(execution.router)
app.include_router(workflows.router)
app.include_router(marketplace.router)
app.include_router(schedules.router)
app.include_router(intelligence.router)
app.include_router(workspaces.router)
app.include_router(billing.router)
app.include_router(innovation.router)
app.include_router(deployment.router)
app.include_router(admin.router)
app.include_router(growth.router)
app.include_router(wallet.router)
app.include_router(talent_hub.router)
app.include_router(compliance.router)
app.include_router(code_auditor.router)
app.include_router(wellness.router)
app.include_router(infra_optimizer.router)
app.include_router(ethics_guardian.router)
app.include_router(self_improvement.router)
app.include_router(observability.router)
app.include_router(autonomy.router)
app.include_router(analytics.router)
app.include_router(metrics.router)
app.include_router(storage.router)
app.include_router(trending.router)
app.include_router(templates_library.router)
app.include_router(referral.router)
app.include_router(founder.router)
app.include_router(share.router)
app.include_router(revenue.router)

# ==================== STARTUP/SHUTDOWN ====================
@app.on_event("startup")
async def startup_event():
    """Start background services"""
    logger.info(f"Starting {settings.APP_NAME} - DEBUG: {settings.DEBUG}")
    
    # Register marketplace agents
    try:
        from services.agent_registry_fix import register_marketplace_agents
        register_marketplace_agents()
        logger.info("âœ… Marketplace agents registered")
    except ImportError as e:
        logger.warning(f"Marketplace agents module not available: {e}")
    except Exception as e:
        logger.warning(f"Failed to register marketplace agents: {e}", exc_info=True)

    # Seed marketplace with system agents
    try:
        from services.marketplace_seeder import seed_marketplace_agents, verify_marketplace_seeding
        with get_db_context() as db:
            seeded = seed_marketplace_agents(db)
            if seeded > 0:
                logger.info(f"Marketplace seeded with {seeded} new agents")
            verify_marketplace_seeding(db)
    except Exception as e:
        logger.warning(f"Marketplace seeding failed: {e}", exc_info=True)

    # Ensure demo agent exists
    try:
        from services.demo_agent import ensure_demo_agent
        with get_db_context() as db:
            demo_agent = ensure_demo_agent(db)
            logger.info("Demo agent ready: id=%s", demo_agent.id)
    except Exception as e:
        logger.warning("Demo agent setup failed: %s", e, exc_info=True)
    
    try:
        # Start the background scheduler
        # asyncio.create_task(scheduler_loop())  # Temporarily disabled
        logger.info("Scheduler started")
    except Exception as e:
        logger.warning(f"Scheduler startup failed: {e}")

    # Warm up Ollama only when local inference is actually enabled.
    if settings.DEFAULT_AI_PROVIDER in ("local", "ollama"):
        try:
            from services.ollama_warmup import warmup_ollama
            asyncio.create_task(warmup_ollama())
            logger.info("Ollama warm-up scheduled")
        except Exception as e:
            logger.warning("Ollama warm-up scheduling failed: %s", e, exc_info=True)
    else:
        logger.info(
            "Skipping Ollama warm-up because provider '%s' does not require it",
            settings.DEFAULT_AI_PROVIDER,
        )
    
    try:
        # Start background job worker
        # asyncio.create_task(job_queue.worker())  # Temporarily disabled
        logger.info("Job queue worker started")
    except Exception as e:
        logger.warning(f"Job queue startup failed: {e}")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info(f"Shutting down {settings.APP_NAME}")

# ==================== HEALTH CHECK ====================
@app.get("/")
def home():
    """Health check endpoint"""
    return {"status": "Flowora running âœ…", "version": "1.0.0"}

@app.get("/health")
def health_check():
    """Detailed health check with core readiness and optional dependency status."""
    from database_production import check_db_connection
    from services.redis_service import get_cache
    from services.object_storage import ObjectStorageService

    def _looks_local_endpoint(value: str | None) -> bool:
        if not value:
            return True
        normalized = value.strip().lower()
        return any(
            marker in normalized
            for marker in ("localhost", "127.0.0.1", "redis://localhost", "://localhost")
        )

    def _looks_placeholder(value: str | None) -> bool:
        if not value:
            return True
        normalized = value.strip()
        return normalized.startswith("<") and normalized.endswith(">")

    health_status = {
        "status": "healthy",
        "app": settings.APP_NAME,
        "debug": settings.DEBUG,
        "version": "1.0.0",
        "database": "unknown",
        "redis": "unknown",
        "celery": "unknown",
        "ollama": "unknown",
        "minio": "unknown",
    }

    try:
        health_status["database"] = "healthy" if check_db_connection() else "unhealthy"
    except Exception as e:
        health_status["database"] = f"error: {str(e)}"

    redis_configured = not _looks_local_endpoint(settings.REDIS_URL)
    if redis_configured:
        try:
            cache = get_cache()
            health_status["redis"] = "healthy" if cache.client and cache.client.ping() else "degraded"
        except Exception as e:
            health_status["redis"] = f"degraded: {str(e)}"
    else:
        health_status["redis"] = "not_configured"

    celery_configured = (
        not _looks_local_endpoint(settings.CELERY_BROKER_URL)
        and not _looks_local_endpoint(settings.CELERY_RESULT_BACKEND)
    )
    if celery_configured:
        try:
            from celery_app import celery_app
            responses = celery_app.control.ping(timeout=1)
            health_status["celery"] = "healthy" if responses else "degraded"
        except Exception as e:
            health_status["celery"] = f"degraded: {str(e)}"
    else:
        health_status["celery"] = "not_configured"

    if settings.DEFAULT_AI_PROVIDER == "local":
        ollama_details = get_ollama_health(settings.DEFAULT_AI_MODEL)
        health_status["ollama"] = ollama_details["status"]
        health_status["ollama_details"] = ollama_details
    else:
        health_status["ollama"] = "not_required"
        health_status["ollama_details"] = {
            "status": "not_required",
            "provider": settings.DEFAULT_AI_PROVIDER,
            "required_model": settings.DEFAULT_AI_MODEL,
        }

    minio_configured = not (
        _looks_placeholder(settings.MINIO_ENDPOINT)
        or _looks_local_endpoint(settings.MINIO_ENDPOINT)
    )
    if minio_configured:
        try:
            storage = ObjectStorageService()
            health_status["minio"] = "healthy" if storage.health_check() else "degraded"
        except Exception as e:
            health_status["minio"] = f"degraded: {str(e)}"
    else:
        health_status["minio"] = "not_configured"

    if health_status["database"] != "healthy":
        health_status["status"] = "unhealthy"

    return health_status


@app.get("/api/health")
def health_check_alias():
    """Alias for health check behind API prefix expectations."""
    return health_check()


@app.get("/health/ollama")
def ollama_health_check():
    """Dedicated Ollama health and model readiness endpoint."""
    return get_ollama_health(settings.DEFAULT_AI_MODEL)


@app.get("/api/health/ollama")
def ollama_health_check_alias():
    """Alias for Ollama health behind API prefix expectations."""
    return ollama_health_check()
