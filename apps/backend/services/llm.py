import httpx
from typing import Optional

from config_production import settings
from services.ai_limiter import ollama_limiter
from services.ollama_service import post_ollama_json

# Default to local Ollama instance
OLLAMA_BASE_URL = settings.OLLAMA_BASE_URL

async def generate_response(prompt: str, model: str = "llama3", system_prompt: Optional[str] = None) -> str:
    """
    Generates a response from the Ollama LLM.
    """
    # Ollama uses /api/generate endpoint
    url = f"{OLLAMA_BASE_URL}/api/generate"
    
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False
    }
    
    if system_prompt:
        payload["system"] = system_prompt
        
    async def _call():
        if OLLAMA_BASE_URL.rstrip("/") != settings.OLLAMA_BASE_URL.rstrip("/"):
            async with httpx.AsyncClient(timeout=settings.OLLAMA_TIMEOUT_SECONDS) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                result = response.json()
        else:
            result = await post_ollama_json(
                path="/api/generate",
                json_body=payload,
                required_model=model,
                read_timeout=settings.OLLAMA_TIMEOUT_SECONDS,
            )
        return result.get("response", "")

    try:
        return await ollama_limiter.run(_call)
    except httpx.RequestError as e:
        print(f"An error occurred while requesting {e.request.url!r}.")
        if not settings.ALLOW_LLM_MOCK_FALLBACK:
            raise RuntimeError(f"Ollama request failed: {e}")
        # Fallback for testing if Ollama is not running
        return f"[Mock LLM Response] processed: {prompt}"
    except httpx.HTTPStatusError as e:
        print(f"Error response {e.response.status_code} while requesting {e.request.url!r}.")
        return f"[Error] LLM service unavailable: {e.response.status_code}"
