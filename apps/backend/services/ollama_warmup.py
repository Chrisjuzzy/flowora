import logging
import httpx

from config_production import settings
from services.ollama_service import ensure_ollama_model_available, post_ollama_json

logger = logging.getLogger(__name__)


async def warmup_ollama() -> None:
    """
    Warm up the Ollama model to avoid first-run timeouts.
    """
    try:
        await ensure_ollama_model_available(settings.DEMO_AGENT_MODEL)
        await post_ollama_json(
            path="/api/generate",
            json_body={
                "model": settings.DEMO_AGENT_MODEL,
                "prompt": "Say 'ready' in one word.",
                "stream": False,
                "options": {"temperature": 0.2},
            },
            required_model=settings.DEMO_AGENT_MODEL,
            read_timeout=settings.OLLAMA_WARMUP_TIMEOUT_SECONDS,
            attempts=1,
        )
        logger.info("Ollama warm-up completed for model %s", settings.DEMO_AGENT_MODEL)
    except (TimeoutError, httpx.TimeoutException, RuntimeError) as exc:
        logger.info("Ollama warmup skipped (non-blocking): %s", exc)
    except Exception as exc:
        logger.warning("Ollama warm-up failed: %s", exc, exc_info=True)
