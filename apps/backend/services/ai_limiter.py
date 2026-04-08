import asyncio
import logging
from typing import Awaitable, Callable, TypeVar

from fastapi import HTTPException
from config_production import settings
from utils.prometheus_metrics import record_llm_timeout

logger = logging.getLogger(__name__)

T = TypeVar("T")


class OllamaLimiter:
    def __init__(self) -> None:
        self._semaphore = asyncio.Semaphore(settings.OLLAMA_MAX_CONCURRENCY)
        self._queue_limit = settings.OLLAMA_QUEUE_MAX
        self._inflight = 0
        self._lock = asyncio.Lock()

    async def run(self, coro_factory: Callable[[], Awaitable[T]]) -> T:
        async with self._lock:
            if self._inflight >= settings.OLLAMA_MAX_CONCURRENCY + self._queue_limit:
                raise HTTPException(
                    status_code=429,
                    detail="AI execution queue is full. Please retry shortly."
                )
            self._inflight += 1

        try:
            async with self._semaphore:
                return await asyncio.wait_for(
                    coro_factory(),
                    timeout=settings.effective_ollama_timeout_seconds
                )
        except asyncio.TimeoutError:
            record_llm_timeout("ollama", settings.DEFAULT_AI_MODEL)
            logger.info(
                "LLM timeout reached in limiter, aborting inference after %ss",
                settings.effective_ollama_timeout_seconds,
            )
            raise HTTPException(
                status_code=504,
                detail="AI execution timed out. Please retry."
            )
        finally:
            async with self._lock:
                self._inflight = max(0, self._inflight - 1)


ollama_limiter = OllamaLimiter()
