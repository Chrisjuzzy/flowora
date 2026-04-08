import asyncio
import logging
from typing import Any

import httpx

from config_production import settings
from utils.prometheus_metrics import record_llm_timeout


logger = logging.getLogger(__name__)

_TRANSIENT_STATUS_CODES = {408, 425, 429, 500, 502, 503, 504}
_verified_models: set[str] = set()
_verification_lock = asyncio.Lock()


def ollama_base_url() -> str:
    return settings.OLLAMA_BASE_URL.rstrip("/")


def ollama_timeout(read_timeout: float | None = None) -> httpx.Timeout:
    connect_timeout = settings.OLLAMA_CONNECT_TIMEOUT_SECONDS
    effective_read_timeout = min(
        read_timeout or settings.effective_ollama_timeout_seconds,
        settings.effective_ollama_timeout_seconds,
    )
    return httpx.Timeout(
        timeout=None,
        connect=connect_timeout,
        read=effective_read_timeout,
        write=connect_timeout,
        pool=connect_timeout,
    )


async def fetch_ollama_tags(
    *,
    attempts: int | None = None,
    required_model: str | None = None,
) -> dict[str, Any]:
    attempts = attempts or settings.OLLAMA_RETRY_ATTEMPTS
    last_error: Exception | None = None
    url = f"{ollama_base_url()}/api/tags"

    for attempt in range(1, attempts + 1):
        try:
            async with httpx.AsyncClient(
                timeout=ollama_timeout(settings.OLLAMA_HEALTH_TIMEOUT_SECONDS)
            ) as client:
                response = await client.get(url)
                response.raise_for_status()
                payload = response.json()
                model_names = {
                    item.get("name")
                    for item in payload.get("models", [])
                    if item.get("name")
                }
                if required_model and required_model not in model_names:
                    raise RuntimeError(
                        f"Ollama is reachable but model '{required_model}' is not loaded."
                    )
                return payload
        except Exception as exc:
            last_error = exc
            if attempt == attempts:
                break
            delay = settings.OLLAMA_RETRY_BACKOFF_SECONDS * attempt
            logger.warning(
                "Ollama readiness probe failed (attempt %s/%s): %s",
                attempt,
                attempts,
                exc,
            )
            await asyncio.sleep(delay)

    raise RuntimeError(f"Ollama readiness failed after {attempts} attempts: {last_error}")


async def ensure_ollama_model_available(model_name: str | None = None) -> dict[str, Any]:
    model_name = model_name or settings.DEFAULT_AI_MODEL
    if model_name in _verified_models:
        return {"status": "cached", "model": model_name}

    async with _verification_lock:
        if model_name in _verified_models:
            return {"status": "cached", "model": model_name}

        payload = await fetch_ollama_tags(required_model=model_name)
        _verified_models.add(model_name)
        return payload


async def post_ollama_json(
    *,
    path: str,
    json_body: dict[str, Any],
    required_model: str | None = None,
    read_timeout: float | None = None,
    attempts: int | None = None,
) -> dict[str, Any]:
    required_model = required_model or json_body.get("model") or settings.DEFAULT_AI_MODEL
    attempts = attempts or settings.OLLAMA_RETRY_ATTEMPTS
    url = f"{ollama_base_url()}{path}"
    effective_read_timeout = min(
        read_timeout or settings.effective_ollama_timeout_seconds,
        settings.effective_ollama_timeout_seconds,
    )

    await ensure_ollama_model_available(required_model)

    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            async with httpx.AsyncClient(timeout=ollama_timeout(effective_read_timeout)) as client:
                response = await client.post(url, json=json_body)
                if response.status_code in _TRANSIENT_STATUS_CODES and attempt < attempts:
                    raise httpx.HTTPStatusError(
                        f"Transient Ollama status {response.status_code}",
                        request=response.request,
                        response=response,
                    )
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as exc:
            last_error = exc
            body = ""
            try:
                body = exc.response.text
            except Exception:
                body = ""

            if exc.response.status_code == 404 and "model" in body.lower():
                _verified_models.discard(required_model)
                if attempt < attempts:
                    await ensure_ollama_model_available(required_model)
            elif exc.response.status_code not in _TRANSIENT_STATUS_CODES or attempt == attempts:
                raise RuntimeError(
                    f"Ollama HTTP error {exc.response.status_code}: {body or exc}"
                ) from exc

            if attempt == attempts:
                break
            delay = settings.OLLAMA_RETRY_BACKOFF_SECONDS * attempt
            logger.warning(
                "Ollama request failed with retryable status (attempt %s/%s): %s",
                attempt,
                attempts,
                exc,
            )
            await asyncio.sleep(delay)
        except (httpx.RequestError, httpx.TimeoutException) as exc:
            last_error = exc
            if isinstance(exc, httpx.TimeoutException):
                logger.info(
                    "LLM timeout reached, aborting inference (model=%s, timeout=%ss)",
                    required_model,
                    effective_read_timeout,
                )
                record_llm_timeout("ollama", required_model)
                raise RuntimeError(
                    f"Ollama request timed out after {effective_read_timeout}s"
                ) from exc
            if attempt == attempts:
                break
            delay = settings.OLLAMA_RETRY_BACKOFF_SECONDS * attempt
            logger.warning(
                "Ollama request transport error (attempt %s/%s): %s",
                attempt,
                attempts,
                exc,
            )
            await asyncio.sleep(delay)
        except asyncio.CancelledError:
            logger.info("Ollama inference task cancelled before completion (model=%s)", required_model)
            raise

    raise RuntimeError(f"Ollama request failed after {attempts} attempts: {last_error}")


def get_ollama_health(required_model: str | None = None) -> dict[str, Any]:
    required_model = required_model or settings.DEFAULT_AI_MODEL
    base_url = ollama_base_url()
    url = f"{base_url}/api/tags"

    try:
        with httpx.Client(timeout=ollama_timeout(settings.OLLAMA_HEALTH_TIMEOUT_SECONDS)) as client:
            response = client.get(url)
            response.raise_for_status()
            payload = response.json()
    except Exception as exc:
        return {
            "status": "unhealthy",
            "base_url": base_url,
            "required_model": required_model,
            "model_available": False,
            "models": [],
            "error": str(exc),
        }

    model_names = [
        item.get("name")
        for item in payload.get("models", [])
        if item.get("name")
    ]
    model_available = required_model in model_names
    return {
        "status": "healthy" if model_available else "degraded",
        "base_url": base_url,
        "required_model": required_model,
        "model_available": model_available,
        "models": model_names,
        "model_count": len(model_names),
    }
