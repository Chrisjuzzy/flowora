
"""
AI Provider Service - Abstraction layer for multiple AI providers
Supports: OpenAI, Anthropic, Google Gemini
"""
from abc import ABC, abstractmethod
import logging
from typing import Dict, Any, Optional

from fastapi import HTTPException
import httpx

from config_production import settings
from services.ollama_service import post_ollama_json

logger = logging.getLogger(__name__)


def _classify_local_provider_error(exc: Exception) -> HTTPException:
    if isinstance(exc, HTTPException):
        return exc

    message = str(exc).lower()
    if "timed out" in message or isinstance(exc, httpx.TimeoutException):
        return HTTPException(status_code=504, detail="AI execution timed out. Please retry.")
    if isinstance(exc, httpx.RequestError):
        return HTTPException(
            status_code=503,
            detail="Local AI service is temporarily unavailable. Please retry.",
        )
    return HTTPException(status_code=502, detail="Local AI inference failed. Please retry.")


class AIProvider(ABC):
    """Abstract base class for AI providers"""

    @abstractmethod
    async def generate(self, prompt: str, system_prompt: Optional[str] = None, 
                     model: Optional[str] = None, temperature: Optional[float] = None) -> str:
        """Generate text from the AI provider"""
        pass

    @abstractmethod
    async def generate_with_metadata(self, prompt: str, system_prompt: Optional[str] = None,
                                  model: Optional[str] = None, temperature: Optional[float] = None) -> Dict[str, Any]:
        """Generate text with metadata (tokens, time, cost)"""
        pass


class LocalProvider(AIProvider):
    """Local Ollama provider (with mock fallback)"""

    def __init__(self, base_url: Optional[str] = None):
        self.base_url = base_url or settings.OLLAMA_BASE_URL

    async def generate(self, prompt: str, system_prompt: Optional[str] = None,
                     model: Optional[str] = None, temperature: Optional[float] = None) -> str:
        result = await self.generate_with_metadata(prompt, system_prompt, model, temperature)
        return result["text"]

    async def generate_with_metadata(self, prompt: str, system_prompt: Optional[str] = None,
                                  model: Optional[str] = None, temperature: Optional[float] = None) -> Dict[str, Any]:
        import time

        model = model or settings.DEFAULT_AI_MODEL
        payload: Dict[str, Any] = {
            "model": model,
            "prompt": prompt,
            "stream": False
        }
        if system_prompt:
            payload["system"] = system_prompt
        options: Dict[str, Any] = {}
        if settings.OLLAMA_NUM_CTX:
            options["num_ctx"] = settings.OLLAMA_NUM_CTX
        if settings.OLLAMA_NUM_PREDICT:
            options["num_predict"] = settings.OLLAMA_NUM_PREDICT
        if settings.OLLAMA_NUM_THREADS:
            options["num_thread"] = settings.OLLAMA_NUM_THREADS
        if temperature is not None:
            options["temperature"] = temperature
        elif settings.OLLAMA_TEMPERATURE is not None:
            options["temperature"] = settings.OLLAMA_TEMPERATURE
        if options:
            payload["options"] = options
        if getattr(settings, "OLLAMA_KEEP_ALIVE", None):
            payload["keep_alive"] = settings.OLLAMA_KEEP_ALIVE

        start_time = time.time()
        try:
            if self.base_url.rstrip("/") != settings.OLLAMA_BASE_URL.rstrip("/"):
                async with httpx.AsyncClient(timeout=settings.OLLAMA_TIMEOUT_SECONDS) as client:
                    response = await client.post(f"{self.base_url}/api/generate", json=payload)
                    response.raise_for_status()
                    data = response.json()
            else:
                data = await post_ollama_json(
                    path="/api/generate",
                    json_body=payload,
                    required_model=model,
                    read_timeout=settings.effective_ollama_timeout_seconds,
                )

            execution_time_ms = int((time.time() - start_time) * 1000)
            total_tokens = (data.get("eval_count", 0) or 0) + (data.get("prompt_eval_count", 0) or 0)

            return {
                "text": data.get("response", ""),
                "token_usage": total_tokens,
                "execution_time_ms": execution_time_ms,
                "cost_estimate": "0.0",
                "model": model,
                "provider": "local"
            }
        except Exception as e:
            mapped_error = _classify_local_provider_error(e)
            if mapped_error.status_code in (429, 504):
                logger.info(
                    "Local provider returned expected %s: %s",
                    mapped_error.status_code,
                    mapped_error.detail,
                )
            else:
                logger.warning(
                    "Local provider error mapped to %s: %s",
                    mapped_error.status_code,
                    mapped_error.detail,
                    exc_info=True,
                )
            if not settings.ALLOW_LLM_MOCK_FALLBACK:
                raise mapped_error
            mock_text = f"[Mock Local Response] {prompt[:120]}"
            return {
                "text": mock_text,
                "token_usage": 0,
                "execution_time_ms": 0,
                "cost_estimate": "0.0",
                "model": model,
                "provider": "local",
                "mock": True
            }


class MockProvider(AIProvider):
    """Deterministic mock provider for safe staging environments."""

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
    ) -> str:
        result = await self.generate_with_metadata(prompt, system_prompt, model, temperature)
        return result["text"]

    async def generate_with_metadata(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
    ) -> Dict[str, Any]:
        snippet = " ".join((prompt or "").strip().split())
        if len(snippet) > 140:
            snippet = snippet[:137] + "..."
        text = f"[Mock Response] {snippet or 'Flowora mock response ready.'}"
        return {
            "text": text,
            "token_usage": 0,
            "execution_time_ms": 1,
            "cost_estimate": "0.0",
            "model": model or "mock",
            "provider": "mock",
            "mock": True,
        }


class OpenAIProvider(AIProvider):
    """OpenAI API provider"""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.OPENAI_API_KEY
        self.base_url = "https://api.openai.com/v1"

    async def generate(self, prompt: str, system_prompt: Optional[str] = None,
                     model: Optional[str] = None, temperature: Optional[float] = None) -> str:
        result = await self.generate_with_metadata(prompt, system_prompt, model, temperature)
        return result["text"]

    async def generate_with_metadata(self, prompt: str, system_prompt: Optional[str] = None,
                                  model: Optional[str] = None, temperature: Optional[float] = None) -> Dict[str, Any]:
        """Generate text using OpenAI API"""
        import time

        model = model or "gpt-3.5-turbo"
        temperature = temperature if temperature is not None else 0.7

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature
        }

        start_time = time.time()

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload
                )
                response.raise_for_status()
                data = response.json()

                end_time = time.time()
                execution_time_ms = int((end_time - start_time) * 1000)

                # Extract token usage
                usage = data.get("usage", {})
                prompt_tokens = usage.get("prompt_tokens", 0)
                completion_tokens = usage.get("completion_tokens", 0)
                total_tokens = usage.get("total_tokens", 0)

                # Estimate cost (simplified pricing)
                cost_per_1k_tokens = 0.002 if "gpt-3.5" in model else 0.02
                cost = (total_tokens / 1000) * cost_per_1k_tokens

                return {
                    "text": data["choices"][0]["message"]["content"],
                    "token_usage": total_tokens,
                    "execution_time_ms": execution_time_ms,
                    "cost_estimate": f"{cost:.6f}",
                    "model": model,
                    "provider": "openai"
                }

        except httpx.HTTPStatusError as e:
            logger.error(f"OpenAI API error: {e.response.status_code} - {e.response.text}")
            raise Exception(f"OpenAI API error: {e.response.status_code}")
        except httpx.RequestError as e:
            logger.error(f"OpenAI request error: {str(e)}")
            raise Exception(f"OpenAI request error: {str(e)}")
        except Exception as e:
            logger.error(f"OpenAI generation error: {str(e)}")
            raise


class AnthropicProvider(AIProvider):
    """Anthropic Claude API provider"""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.ANTHROPIC_API_KEY
        self.base_url = "https://api.anthropic.com/v1"

    async def generate(self, prompt: str, system_prompt: Optional[str] = None,
                     model: Optional[str] = None, temperature: Optional[float] = None) -> str:
        result = await self.generate_with_metadata(prompt, system_prompt, model, temperature)
        return result["text"]

    async def generate_with_metadata(self, prompt: str, system_prompt: Optional[str] = None,
                                  model: Optional[str] = None, temperature: Optional[float] = None) -> Dict[str, Any]:
        """Generate text using Anthropic API"""
        import time

        model = model or "claude-3-opus-20240229"
        temperature = temperature if temperature is not None else 0.7

        headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01"
        }

        payload = {
            "model": model,
            "max_tokens": 4096,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature
        }

        if system_prompt:
            payload["system"] = system_prompt

        start_time = time.time()

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.base_url}/messages",
                    headers=headers,
                    json=payload
                )
                response.raise_for_status()
                data = response.json()

                end_time = time.time()
                execution_time_ms = int((end_time - start_time) * 1000)

                # Extract token usage
                usage = data.get("usage", {})
                input_tokens = usage.get("input_tokens", 0)
                output_tokens = usage.get("output_tokens", 0)
                total_tokens = input_tokens + output_tokens

                # Estimate cost (simplified pricing)
                cost_per_1k_input = 0.015 if "opus" in model else 0.003
                cost_per_1k_output = 0.075 if "opus" in model else 0.015
                cost = ((input_tokens / 1000) * cost_per_1k_input + 
                        (output_tokens / 1000) * cost_per_1k_output)

                return {
                    "text": data["content"][0]["text"],
                    "token_usage": total_tokens,
                    "execution_time_ms": execution_time_ms,
                    "cost_estimate": f"{cost:.6f}",
                    "model": model,
                    "provider": "anthropic"
                }

        except httpx.HTTPStatusError as e:
            logger.error(f"Anthropic API error: {e.response.status_code} - {e.response.text}")
            raise Exception(f"Anthropic API error: {e.response.status_code}")
        except httpx.RequestError as e:
            logger.error(f"Anthropic request error: {str(e)}")
            raise Exception(f"Anthropic request error: {str(e)}")
        except Exception as e:
            logger.error(f"Anthropic generation error: {str(e)}")
            raise


class GeminiProvider(AIProvider):
    """Google Gemini API provider"""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.GEMINI_API_KEY
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"

    async def generate(self, prompt: str, system_prompt: Optional[str] = None,
                     model: Optional[str] = None, temperature: Optional[float] = None) -> str:
        result = await self.generate_with_metadata(prompt, system_prompt, model, temperature)
        return result["text"]

    async def generate_with_metadata(self, prompt: str, system_prompt: Optional[str] = None,
                                  model: Optional[str] = None, temperature: Optional[float] = None) -> Dict[str, Any]:
        """Generate text using Google Gemini API"""
        import time

        model = model or "gemini-pro"
        temperature = temperature if temperature is not None else 0.7

        # Combine system prompt with user prompt for Gemini
        full_prompt = prompt
        if system_prompt:
            full_prompt = f"{system_prompt}\n\n{prompt}"

        params = {
            "key": self.api_key
        }

        payload = {
            "contents": [{"parts": [{"text": full_prompt}]}],
            "generationConfig": {
                "temperature": temperature,
                "topK": 1,
                "topP": 1,
                "maxOutputTokens": 8192,
            }
        }

        start_time = time.time()

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.base_url}/models/{model}:generateContent",
                    params=params,
                    json=payload
                )
                response.raise_for_status()
                data = response.json()

                end_time = time.time()
                execution_time_ms = int((end_time - start_time) * 1000)

                # Extract text and token usage
                text = data["candidates"][0]["content"]["parts"][0]["text"]
                usage_metadata = data.get("usageMetadata", {})
                total_tokens = usage_metadata.get("totalTokenCount", 0)

                # Estimate cost (simplified pricing)
                cost_per_1k_tokens = 0.001
                cost = (total_tokens / 1000) * cost_per_1k_tokens

                return {
                    "text": text,
                    "token_usage": total_tokens,
                    "execution_time_ms": execution_time_ms,
                    "cost_estimate": f"{cost:.6f}",
                    "model": model,
                    "provider": "gemini"
                }

        except httpx.HTTPStatusError as e:
            logger.error(f"Gemini API error: {e.response.status_code} - {e.response.text}")
            raise Exception(f"Gemini API error: {e.response.status_code}")
        except httpx.RequestError as e:
            logger.error(f"Gemini request error: {str(e)}")
            raise Exception(f"Gemini request error: {str(e)}")
        except Exception as e:
            logger.error(f"Gemini generation error: {str(e)}")
            raise


class AIProviderFactory:
    """Factory for creating AI provider instances"""

    @staticmethod
    def get_provider(provider_name: str = "openai", api_key: Optional[str] = None) -> AIProvider:
        """Get an AI provider instance by name"""
        provider_name = provider_name.lower()

        if provider_name == "openai":
            return OpenAIProvider(api_key)
        elif provider_name == "anthropic":
            return AnthropicProvider(api_key)
        elif provider_name == "gemini":
            return GeminiProvider(api_key)
        elif provider_name == "mock":
            return MockProvider()
        elif provider_name in ("local", "ollama"):
            return LocalProvider()
        else:
            logger.warning(f"Unknown provider '{provider_name}', defaulting to OpenAI")
            return OpenAIProvider(api_key)


# Convenience functions for running agents with specific providers
async def run_openai_agent(prompt: str, system_prompt: Optional[str] = None,
                           model: Optional[str] = None, temperature: Optional[float] = None,
                           api_key: Optional[str] = None) -> str:
    """Run an agent using OpenAI"""
    provider = OpenAIProvider(api_key)
    return await provider.generate(prompt, system_prompt, model, temperature)


async def run_anthropic_agent(prompt: str, system_prompt: Optional[str] = None,
                              model: Optional[str] = None, temperature: Optional[float] = None,
                              api_key: Optional[str] = None) -> str:
    """Run an agent using Anthropic"""
    provider = AnthropicProvider(api_key)
    return await provider.generate(prompt, system_prompt, model, temperature)


async def run_gemini_agent(prompt: str, system_prompt: Optional[str] = None,
                          model: Optional[str] = None, temperature: Optional[float] = None,
                          api_key: Optional[str] = None) -> str:
    """Run an agent using Google Gemini"""
    provider = GeminiProvider(api_key)
    return await provider.generate(prompt, system_prompt, model, temperature)
