
"""
Production Configuration for Flowora SaaS Platform
Enhanced with PostgreSQL, Redis, Celery, and comprehensive error handling
"""
from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    # ==================== APP CONFIGURATION ====================
    APP_NAME: str = "Flowora"
    DEBUG: bool = False  # Set to False in production
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = "development"  # development, staging, production
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # ==================== DATABASE ====================
    DATABASE_URL: str = "postgresql://user:password@localhost:5432/aiagentbuilder"
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 10
    DATABASE_POOL_TIMEOUT: int = 30
    DATABASE_POOL_RECYCLE: int = 3600  # Recycle connections after 1 hour
    DATABASE_ECHO: bool = False
    DATABASE_CONNECT_TIMEOUT_SECONDS: int = 5
    DATABASE_STARTUP_MAX_ATTEMPTS: int = 12
    DATABASE_STARTUP_BACKOFF_SECONDS: float = 2.0
    DATABASE_STARTUP_MAX_BACKOFF_SECONDS: float = 10.0

    # ==================== REDIS ====================
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_MAX_CONNECTIONS: int = 50
    REDIS_SOCKET_TIMEOUT: int = 5
    REDIS_SOCKET_CONNECT_TIMEOUT: int = 5
    REDIS_DECODE_RESPONSES: bool = True

    # ==================== CELERY ====================
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"
    CELERY_TASK_TRACK_STARTED: bool = True
    CELERY_TASK_TIME_LIMIT: int = 300  # 5 minutes
    CELERY_TASK_SOFT_TIME_LIMIT: int = 240  # 4 minutes
    CELERY_WORKER_PREFETCH_MULTIPLIER: int = 4
    CELERY_WORKER_CONCURRENCY: int = 4
    CELERY_ACKS_LATE: bool = True
    CELERY_REJECT_ON_WORKER_LOST: bool = True
    CELERY_MAX_QUEUE_SIZE: int = 1000
    CELERY_MAX_TASKS_PER_CHILD: int = 100
    CELERY_MAX_MEMORY_PER_CHILD_MB: int = 512

    # ==================== SECURITY ====================
    SECRET_KEY: str  # MUST be set via environment variable
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ==================== RATE LIMITING ====================
    RATE_LIMIT_AUTH_PER_MINUTE: int = 10
    RATE_LIMIT_API_PER_MINUTE: int = 30
    RATE_LIMIT_EXECUTION_PER_MINUTE: int = 5
    RATE_LIMIT_WORKFLOW_PER_MINUTE: int = 5
    RATE_LIMIT_USER_PER_MINUTE: int = 60
    RATE_LIMIT_ENABLED: bool = True

    # ==================== PROMPT SAFETY ====================
    PROMPT_FILTER_ENABLED: bool = True
    PROMPT_MAX_CHARS: int = 4000
    PROMPT_BLOCKLIST: str = ""

    # ==================== CORS ====================
    FRONTEND_URL: str = "http://localhost:3000"  # Frontend domain for CORS
    ALLOWED_ORIGINS: str = "http://localhost:3000,http://localhost:8000"

    # ==================== EMAIL (SMTP) ====================
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    EMAIL_FROM: str = "noreply@flowora.ai"
    EMAIL_VERIFICATION_REQUIRED: bool = True
    AUTO_VERIFY_EMAIL: bool = False
    EMAIL_VERIFICATION_TOKEN_TTL_MINUTES: int = 30

    # ==================== OBJECT STORAGE (MINIO) ====================
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_BUCKET: str = "flowora"
    MINIO_SECURE: bool = False

    # ==================== AI PROVIDERS ====================
    DEFAULT_AI_PROVIDER: str = "local"  # openai, anthropic, gemini, local
    DEFAULT_AI_MODEL: str = "qwen2.5:7b-instruct"
    OLLAMA_BASE_URL: str = "http://ollama:11434"
    OLLAMA_PRELOAD_MODEL: str = "qwen2.5:7b-instruct"
    ALLOW_LLM_MOCK_FALLBACK: bool = False
    OLLAMA_NUM_CTX: int = 2048
    OLLAMA_NUM_PREDICT: int = 128
    OLLAMA_NUM_THREADS: int = 4
    OLLAMA_KEEP_ALIVE: str = "30m"
    OLLAMA_TEMPERATURE: float = 0.2
    OLLAMA_CONNECT_TIMEOUT_SECONDS: int = 5
    OLLAMA_HEALTH_TIMEOUT_SECONDS: int = 5
    OLLAMA_RETRY_ATTEMPTS: int = 6
    OLLAMA_RETRY_BACKOFF_SECONDS: float = 2.0
    OLLAMA_WARMUP_TIMEOUT_SECONDS: int = 15

    # ==================== DEMO AGENT ====================
    DEMO_AGENT_NAME: str = "Flowora Demo Agent"
    DEMO_AGENT_DESCRIPTION: str = "Try Flowora with a ready-to-run public demo agent."
    DEMO_AGENT_SYSTEM_PROMPT: str = (
        "You are Flowora's public demo agent. Respond with concise, helpful output and clear formatting."
    )
    DEMO_AGENT_MODEL: str = "qwen2.5:7b-instruct"

    # OpenAI Configuration
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MAX_RETRIES: int = 3
    OPENAI_RETRY_DELAY: int = 1  # seconds
    OPENAI_TIMEOUT: int = 60  # seconds

    # Anthropic Configuration
    ANTHROPIC_API_KEY: Optional[str] = None
    ANTHROPIC_MAX_RETRIES: int = 3
    ANTHROPIC_RETRY_DELAY: int = 1  # seconds
    ANTHROPIC_TIMEOUT: int = 60  # seconds

    # Google Gemini Configuration
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MAX_RETRIES: int = 3
    GEMINI_RETRY_DELAY: int = 1  # seconds
    GEMINI_TIMEOUT: int = 60  # seconds

    # ==================== FEATURE FLAGS ====================
    ENABLE_MARKETPLACE: bool = True
    ENABLE_SCHEDULING: bool = True
    ENABLE_CODE_STUDIO: bool = True
    ENABLE_CACHING: bool = True
    ENABLE_ASYNC_EXECUTION: bool = True

    # ==================== LOGGING ====================
    LOG_LEVEL: str = "INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL
    LOG_FILE: Optional[str] = None  # Optional log file path
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    LOG_DATE_FORMAT: str = "%Y-%m-%d %H:%M:%S"
    LOG_ROTATION: bool = True
    LOG_MAX_BYTES: int = 104857600  # 100MB
    LOG_BACKUP_COUNT: int = 10
    LOG_COMPRESS: bool = True

    # ==================== MONITORING ====================
    ENABLE_METRICS: bool = True
    METRICS_PORT: int = 9090
    ENABLE_HEALTH_CHECK: bool = True
    HEALTH_CHECK_INTERVAL: int = 30  # seconds

    # ==================== TOOLING ====================
    HTTP_TOOL_ALLOWLIST: str = ""  # Comma-separated domains allowed; empty = allow all
    HTTP_TOOL_BLOCKLIST: str = ""  # Comma-separated domains blocked
    HTTP_TOOL_TIMEOUT_SECONDS: int = 10
    HTTP_TOOL_MAX_CHARS: int = 20000

    DB_TOOL_MAX_ROWS: int = 200

    CODE_TOOL_MAX_CHARS: int = 4000
    CODE_TOOL_TIMEOUT_SECONDS: int = 5
    CODE_TOOL_MAX_OUTPUT_CHARS: int = 4000

    WEB_AUTOMATION_MAX_CHARS: int = 20000

    DOC_TOOL_MAX_CHARS: int = 20000
    DOC_TOOL_MAX_BYTES: int = 5000000

    # ==================== EXECUTION LIMITS ====================
    OLLAMA_MAX_CONCURRENCY: int = 2
    OLLAMA_QUEUE_MAX: int = 4
    OLLAMA_TIMEOUT_SECONDS: int = 110
    REQUEST_TIMEOUT_SECONDS: int = 120
    AGENT_RUN_TIMEOUT_SECONDS: int = 120
    TIMEOUT_BUFFER_SECONDS: int = 10
    WORKFLOW_MAX_DEPTH: int = 20
    WORKFLOW_MAX_EXECUTION_SECONDS: int = 120
    ENABLE_REFLECTION: bool = True
    REFLECTION_MODE: str = "background"  # off, background
    REFLECTION_TIMEOUT_SECONDS: int = 4
    REFLECTION_MAX_CONCURRENCY: int = 1
    REFLECTION_MAX_PENDING_TASKS: int = 8
    REFLECTION_MAX_INPUT_CHARS: int = 600
    REFLECTION_MAX_RESULT_CHARS: int = 1200
    REFLECTION_LOG_COOLDOWN_SECONDS: int = 300
    ENABLE_REFLECTION_EVOLUTION: bool = False
    REFLECTION_EVOLUTION_TIMEOUT_SECONDS: int = 5

    @property
    def effective_request_timeout_seconds(self) -> int:
        return max(1, self.REQUEST_TIMEOUT_SECONDS or self.AGENT_RUN_TIMEOUT_SECONDS)

    @property
    def effective_ollama_timeout_seconds(self) -> int:
        ceiling = max(1, self.effective_request_timeout_seconds - self.TIMEOUT_BUFFER_SECONDS)
        return max(1, min(self.OLLAMA_TIMEOUT_SECONDS, ceiling))

    # ==================== CONTINUOUS LEARNING ====================
    LEARNING_MIN_RUNS: int = 5
    LEARNING_SUCCESS_THRESHOLD: float = 0.7
    LEARNING_EVAL_WINDOW_HOURS: int = 6

    # ==================== PUBLIC EMBED RATE LIMIT ====================
    PUBLIC_EMBED_RATE_LIMIT: int = 10
    PUBLIC_EMBED_RATE_WINDOW_SECONDS: int = 60

    # ==================== VALIDATION ====================
    def validate_required_fields(self) -> None:
        """Validate that all required fields are set"""
        required_fields = {
            'SECRET_KEY': self.SECRET_KEY,
            'DATABASE_URL': self.DATABASE_URL,
            'REDIS_URL': self.REDIS_URL,
        }

        missing_fields = [field for field, value in required_fields.items() 
                        if not value or value.strip() == '']

        if missing_fields:
            raise ValueError(
                f"Missing required environment variables: {', '.join(missing_fields)}"
            )

        # Validate AI provider keys if provider is set
        if self.DEFAULT_AI_PROVIDER == "openai" and not self.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY is required when using OpenAI provider")
        if self.DEFAULT_AI_PROVIDER == "anthropic" and not self.ANTHROPIC_API_KEY:
            raise ValueError("ANTHROPIC_API_KEY is required when using Anthropic provider")
        if self.DEFAULT_AI_PROVIDER == "gemini" and not self.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY is required when using Gemini provider")

    class Config:
        env_file = ".env"
        extra = "ignore"
        case_sensitive = True


# Create settings instance
settings = Settings()

# Validate required fields on import
try:
    settings.validate_required_fields()
except ValueError as e:
    import sys
    print(f"Configuration Error: {e}")
    print("Please set all required environment variables in .env file")
    sys.exit(1)
