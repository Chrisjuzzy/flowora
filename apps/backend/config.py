from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # ==================== APP CONFIGURATION ====================
    APP_NAME: str = "Flowora"
    DEBUG: bool = False  # Set to False in production
    API_V1_STR: str = "/api/v1"
    
    # ==================== DATABASE ====================
    DATABASE_URL: str = "sqlite:///./app.db"  # Override with PostgreSQL in production
    DATABASE_CONNECT_TIMEOUT_SECONDS: int = 5
    DATABASE_STARTUP_MAX_ATTEMPTS: int = 12
    DATABASE_STARTUP_BACKOFF_SECONDS: float = 2.0
    DATABASE_STARTUP_MAX_BACKOFF_SECONDS: float = 10.0

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
    AUTO_VERIFY_EMAIL: bool = True
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
    
    # Anthropic Configuration
    ANTHROPIC_API_KEY: Optional[str] = None
    
    # Google Gemini Configuration
    GEMINI_API_KEY: Optional[str] = None
    
    # ==================== FEATURE FLAGS ====================
    ENABLE_MARKETPLACE: bool = True
    ENABLE_SCHEDULING: bool = True
    ENABLE_CODE_STUDIO: bool = True
    ENABLE_ASYNC_EXECUTION: bool = True
    
    # ==================== LOGGING ====================
    LOG_LEVEL: str = "INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL
    LOG_FILE: Optional[str] = None  # Optional log file path
    LOG_MAX_BYTES: int = 104857600  # 100MB
    LOG_BACKUP_COUNT: int = 10
    LOG_COMPRESS: bool = True

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

    class Config:
        env_file = ".env"
        extra = "ignore"
        case_sensitive = True

settings = Settings()
