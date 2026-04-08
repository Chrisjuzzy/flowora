
"""
Production Database Configuration for Flowora
Supports PostgreSQL with connection pooling and error handling
"""
from sqlalchemy import create_engine, text, inspect, event, or_
from sqlalchemy.orm import sessionmaker, Session, with_loader_criteria
from sqlalchemy.pool import QueuePool
from sqlalchemy.orm import declarative_base
from contextlib import contextmanager
import logging
import os
from fastapi import HTTPException
from config_production import settings

logger = logging.getLogger(__name__)

USE_PGVECTOR = os.getenv("USE_PGVECTOR", "true").strip().lower() in {"1", "true", "yes", "on"}

# Create database engine with connection pooling
engine = None
SessionLocal = None
Base = None

def resolve_model_base():
    """
    Use the same Base as the ORM models to ensure tables are created correctly.
    Falls back to a local Base if models cannot be imported.
    """
    try:
        from database import Base as ModelBase
        return ModelBase
    except Exception as e:
        logger.warning(f"Falling back to local Base (model import failed): {e}")
        return declarative_base()


def get_database_url() -> str:
    """Get the database URL from settings."""
    db_url = settings.DATABASE_URL.strip()
    if db_url.startswith("postgres://"):
        db_url = "postgresql://" + db_url[len("postgres://"):]
    return db_url


def create_database_engine():
    """Create SQLAlchemy engine with production settings"""
    global engine, SessionLocal, Base

    try:
        db_url = get_database_url()
        engine_kwargs = {
            "poolclass": QueuePool,
            "pool_size": settings.DATABASE_POOL_SIZE,
            "max_overflow": settings.DATABASE_MAX_OVERFLOW,
            "pool_timeout": settings.DATABASE_POOL_TIMEOUT,
            "pool_recycle": settings.DATABASE_POOL_RECYCLE,
            "pool_pre_ping": True,  # Verify connections before using
            "echo": settings.DATABASE_ECHO,
            "future": True  # Use SQLAlchemy 2.0 style
        }

        # Keep DB connect failures short so startup retries can recover cleanly.
        if db_url.startswith("postgres"):
            engine_kwargs["connect_args"] = {
                "connect_timeout": settings.DATABASE_CONNECT_TIMEOUT_SECONDS
            }

        # SQLite needs check_same_thread disabled for FastAPI concurrency
        if db_url.startswith("sqlite"):
            engine_kwargs["connect_args"] = {"check_same_thread": False}

        engine = create_engine(db_url, **engine_kwargs)

        SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=engine,
            expire_on_commit=False
        )

        Base = resolve_model_base()

        try:
            from database import TenantMixin

            @event.listens_for(SessionLocal, "do_orm_execute")
            def _add_tenant_criteria(execute_state):
                from tenancy import get_current_tenant
                tenant_id = get_current_tenant()
                if tenant_id is None:
                    return
                execute_state.statement = execute_state.statement.options(
                    with_loader_criteria(
                        TenantMixin,
                        lambda cls: or_(cls.tenant_id == tenant_id, cls.tenant_id.is_(None)),
                        include_aliases=True
                    )
                )
        except Exception as exc:
            logger.warning(f"Tenant criteria hook not installed: {exc}")

        logger.info("Database engine created successfully")
        return engine, SessionLocal, Base

    except Exception as e:
        logger.error(f"Failed to create database engine: {e}")
        raise


# Initialize database engine on module load
try:
    engine, SessionLocal, Base = create_database_engine()
except Exception as e:
    logger.error(f"Failed to initialize database: {e}")
    raise


def get_db():
    """
    Dependency function to get database session
    Ensures proper session management and cleanup
    """
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        if isinstance(e, HTTPException) and e.status_code < 500:
            logger.info(f"Database session rollback for handled HTTP exception: {e.status_code} {e.detail}")
        elif isinstance(e, HTTPException):
            logger.warning(f"Database session rollback for HTTP exception: {e.status_code} {e.detail}")
        else:
            logger.error(f"Database session error: {e}")
        db.rollback()
        raise
    finally:
        db.close()


@contextmanager
def get_db_context():
    """
    Context manager for database sessions
    Use for non-FastAPI contexts
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception as e:
        if isinstance(e, HTTPException) and e.status_code < 500:
            logger.info(f"Database context rollback for handled HTTP exception: {e.status_code} {e.detail}")
        elif isinstance(e, HTTPException):
            logger.warning(f"Database context rollback for HTTP exception: {e.status_code} {e.detail}")
        else:
            logger.error(f"Database context error: {e}")
        db.rollback()
        raise
    finally:
        db.close()


def init_db():
    """
    Initialize database tables
    Call this on application startup
    """
    try:
        ensure_postgres_extensions()
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database tables: {e}")
        raise


def ensure_postgres_extensions(connection=None) -> None:
    """
    Enable required PostgreSQL extensions before ORM table creation.
    """
    active_engine = connection.engine if connection is not None else engine
    if not active_engine:
        logger.warning("Database engine not initialized; skipping extension check")
        return

    db_url = str(active_engine.url)
    if not db_url.startswith("postgres"):
        return
    if not USE_PGVECTOR:
        logger.info("pgvector disabled via USE_PGVECTOR; skipping extension check")
        return

    def _ensure(conn):
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))

    try:
        if connection is not None:
            _ensure(connection)
        else:
            with active_engine.begin() as conn:
                _ensure(conn)
        logger.info("PostgreSQL extensions verified")
    except Exception as e:
        logger.error(f"Failed to ensure PostgreSQL extensions: {e}", exc_info=True)
        raise


def ensure_required_tables(required_tables: list[str]) -> None:
    """
    Ensure critical tables exist in the database.
    Logs missing tables after attempting to create them.
    """
    if not engine or not Base:
        logger.warning("Database engine not initialized; skipping table check")
        return

    try:
        inspector = inspect(engine)
        existing_tables = set(inspector.get_table_names())
        missing = [t for t in required_tables if t not in existing_tables]

        if missing:
            logger.warning(f"Missing tables detected: {missing}. Attempting create_all.")
            ensure_postgres_extensions()
            Base.metadata.create_all(bind=engine)
            inspector = inspect(engine)
            existing_tables = set(inspector.get_table_names())
            still_missing = [t for t in required_tables if t not in existing_tables]
            if still_missing:
                logger.error(f"Tables still missing after create_all: {still_missing}")
            else:
                logger.info("All required tables are present after create_all.")
        else:
            logger.info("All required tables are present.")
    except Exception as e:
        logger.error(f"Failed to verify required tables: {e}", exc_info=True)


def ensure_sqlite_schema() -> None:
    """
    Ensure SQLite schema stays in sync with ORM models for critical columns.
    Only runs for SQLite databases.
    """
    if not engine:
        return

    db_url = str(engine.url)
    if not db_url.startswith("sqlite"):
        return

    try:
        with engine.begin() as conn:
            inspector = inspect(engine)
            for table_name in inspector.get_table_names():
                result = conn.execute(text(f"PRAGMA table_info({table_name})"))
                existing_cols = {row[1] for row in result.fetchall()}
                if "tenant_id" not in existing_cols:
                    logger.info(f"Adding missing column to {table_name}: tenant_id")
                    conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN tenant_id INTEGER"))

            # Ensure agents table columns exist
            result = conn.execute(text("PRAGMA table_info(agents)"))
            existing_cols = {row[1] for row in result.fetchall()}

            columns_to_add = {
                "ai_provider": "ai_provider TEXT DEFAULT 'openai'",
                "model_name": "model_name TEXT DEFAULT 'gpt-3.5-turbo'",
                "temperature": "temperature FLOAT DEFAULT 0.7"
            }

            for col_name, ddl in columns_to_add.items():
                if col_name not in existing_cols:
                    logger.info(f"Adding missing column to agents: {col_name}")
                    conn.execute(text(f"ALTER TABLE agents ADD COLUMN {ddl}"))

            # Ensure shared_knowledge has reinforcement_score
            result = conn.execute(text("PRAGMA table_info(shared_knowledge)"))
            shared_cols = {row[1] for row in result.fetchall()}
            if "reinforcement_score" not in shared_cols:
                logger.info("Adding missing column to shared_knowledge: reinforcement_score")
                conn.execute(text("ALTER TABLE shared_knowledge ADD COLUMN reinforcement_score INTEGER DEFAULT 0"))

            # Ensure users table has organization_id
            result = conn.execute(text("PRAGMA table_info(users)"))
            user_cols = {row[1] for row in result.fetchall()}
            if "organization_id" not in user_cols:
                logger.info("Adding missing column to users: organization_id")
                conn.execute(text("ALTER TABLE users ADD COLUMN organization_id INTEGER"))

            # Ensure workspaces table has organization_id
            result = conn.execute(text("PRAGMA table_info(workspaces)"))
            workspace_cols = {row[1] for row in result.fetchall()}
            if "organization_id" not in workspace_cols:
                logger.info("Adding missing column to workspaces: organization_id")
                conn.execute(text("ALTER TABLE workspaces ADD COLUMN organization_id INTEGER"))

            # Ensure marketplace_listings has new fields
            result = conn.execute(text("PRAGMA table_info(marketplace_listings)"))
            listing_cols = {row[1] for row in result.fetchall()}
            if "resource_type" not in listing_cols:
                logger.info("Adding missing column to marketplace_listings: resource_type")
                conn.execute(text("ALTER TABLE marketplace_listings ADD COLUMN resource_type TEXT DEFAULT 'agent'"))
            if "resource_id" not in listing_cols:
                logger.info("Adding missing column to marketplace_listings: resource_id")
                conn.execute(text("ALTER TABLE marketplace_listings ADD COLUMN resource_id INTEGER"))
            if "downloads" not in listing_cols:
                logger.info("Adding missing column to marketplace_listings: downloads")
                conn.execute(text("ALTER TABLE marketplace_listings ADD COLUMN downloads INTEGER DEFAULT 0"))
            if "rating" not in listing_cols:
                logger.info("Adding missing column to marketplace_listings: rating")
                conn.execute(text("ALTER TABLE marketplace_listings ADD COLUMN rating FLOAT DEFAULT 0.0"))
            if "version" not in listing_cols:
                logger.info("Adding missing column to marketplace_listings: version")
                conn.execute(text("ALTER TABLE marketplace_listings ADD COLUMN version TEXT DEFAULT '1.0.0'"))

            # Ensure workflows table has sharing fields
            result = conn.execute(text("PRAGMA table_info(workflows)"))
            workflow_cols = {row[1] for row in result.fetchall()}
            if "description" not in workflow_cols:
                logger.info("Adding missing column to workflows: description")
                conn.execute(text("ALTER TABLE workflows ADD COLUMN description TEXT"))
            if "is_public" not in workflow_cols:
                logger.info("Adding missing column to workflows: is_public")
                conn.execute(text("ALTER TABLE workflows ADD COLUMN is_public BOOLEAN DEFAULT 0"))
            if "clone_count" not in workflow_cols:
                logger.info("Adding missing column to workflows: clone_count")
                conn.execute(text("ALTER TABLE workflows ADD COLUMN clone_count INTEGER DEFAULT 0"))
            if "install_count" not in workflow_cols:
                logger.info("Adding missing column to workflows: install_count")
                conn.execute(text("ALTER TABLE workflows ADD COLUMN install_count INTEGER DEFAULT 0"))

            # Ensure executions table has prompt_version_id
            result = conn.execute(text("PRAGMA table_info(executions)"))
            execution_cols = {row[1] for row in result.fetchall()}
            if "prompt_version_id" not in execution_cols:
                logger.info("Adding missing column to executions: prompt_version_id")
                conn.execute(text("ALTER TABLE executions ADD COLUMN prompt_version_id INTEGER"))

            # Ensure execution_logs table has prompt_version_id
            result = conn.execute(text("PRAGMA table_info(execution_logs)"))
            log_cols = {row[1] for row in result.fetchall()}
            if "prompt_version_id" not in log_cols:
                logger.info("Adding missing column to execution_logs: prompt_version_id")
                conn.execute(text("ALTER TABLE execution_logs ADD COLUMN prompt_version_id INTEGER"))

            # Ensure agent_runs table has prompt_version_id
            result = conn.execute(text("PRAGMA table_info(agent_runs)"))
            run_cols = {row[1] for row in result.fetchall()}
            if "prompt_version_id" not in run_cols:
                logger.info("Adding missing column to agent_runs: prompt_version_id")
                conn.execute(text("ALTER TABLE agent_runs ADD COLUMN prompt_version_id INTEGER"))

            # Ensure referrals table has reward_points and referred_user_id
            result = conn.execute(text("PRAGMA table_info(referrals)"))
            referral_cols = {row[1] for row in result.fetchall()}
            if "reward_points" not in referral_cols:
                logger.info("Adding missing column to referrals: reward_points")
                conn.execute(text("ALTER TABLE referrals ADD COLUMN reward_points INTEGER DEFAULT 0"))
            if "referred_user_id" not in referral_cols:
                logger.info("Adding missing column to referrals: referred_user_id")
                conn.execute(text("ALTER TABLE referrals ADD COLUMN referred_user_id INTEGER"))
    except Exception as e:
        logger.error(f"Failed to ensure SQLite schema: {e}", exc_info=True)


def check_db_connection():
    """
    Check database connection health
    Returns True if connection is healthy
    """
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.error(f"Database connection check failed: {e}")
        return False


def close_db_connections():
    """
    Close all database connections
    Call this on application shutdown
    """
    try:
        if engine:
            engine.dispose()
            logger.info("Database connections closed successfully")
    except Exception as e:
        logger.error(f"Failed to close database connections: {e}")
