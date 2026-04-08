
"""
Production AI Provider Service with Retry Logic and Timeout Protection
Enhanced version with comprehensive error handling and resilience
"""
import httpx
import logging
import asyncio
from typing import Dict, Any, Optional
from abc import ABC, abstractmethod
from config_production import settings
from utils.logger_config import get_logger

logger = get_logger(__name__)


class AIProvider(ABC):
    """Abstract base class for AI providers with retry logic"""

    def __init__(self, max_retries: int = None, retry_delay: int = None, timeout: int = None):
        self.max_retries = max_retries or 3
        self.retry_delay = retry_delay or 1
        self.timeout = timeout or 60

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

    async def generate_with_retry(self, prompt: str, system_prompt: Optional[str] = None,
                              model: Optional[str] = None, temperature: Optional[float] = None) -> Dict[str, Any]:
        """
        Generate text with automatic retry logic

        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            model: Optional model name
            temperature: Optional temperature

        Returns:
            Dict with generation results

        Raises:
            Exception: If all retries are exhausted
        """
        last_exception = None

        for attempt in range(self.max_retries):
            try:
                logger.debug(f"Attempt {attempt + 1}/{self.max_retries} for {self.__class__.__name__}")
                result = await self.generate_with_metadata(prompt, system_prompt, model, temperature)

                if attempt > 0:
                    logger.info(f"Successfully generated after {attempt + 1} attempts")

                return result

            except httpx.TimeoutException as e:
                last_exception = e
                logger.warning(f"Timeout on attempt {attempt + 1}: {e}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay * (attempt + 1))

            except httpx.HTTPStatusError as e:
                last_exception = e
                logger.warning(f"HTTP error on attempt {attempt + 1}: {e.response.status_code}")

                # Don't retry on client errors (4xx)
                if 400 <= e.response.status_code < 500:
                    raise

                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay * (attempt + 1))

            except httpx.RequestError as e:
                last_exception = e
                logger.warning(f"Request error on attempt {attempt + 1}: {e}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay * (attempt + 1))

            except Exception as e:
                last_exception = e
                logger.error(f"Unexpected error on attempt {attempt + 1}: {e}")
                raise

        # All retries exhausted
        logger.error(f"All {self.max_retries} attempts exhausted for {self.__class__.__name__}")
        raise Exception(f"Failed after {self.max_retries} attempts: {str(last_exception)}")


class OpenAIProvider(AIProvider):
    """OpenAI API provider with retry logic"""

    def __init__(self, api_key: Optional[str] = None, max_retries: int = None, 
                 retry_delay: int = None, timeout: int = None):
        super().__init__(max_retries, retry_delay, timeout)
        self.api_key = api_key or settings.OPENAI_API_KEY
        self.base_url = "https://api.openai.com/v1"
        self.max_retries = max_retries or settings.OPENAI_MAX_RETRIES
        self.retry_delay = retry_delay or settings.OPENAI_RETRY_DELAY
        self.timeout = timeout or settings.OPENAI_TIMEOUT

    async def generate(self, prompt: str, system_prompt: Optional[str] = None,
                     model: Optional[str] = None, temperature: Optional[float] = None) -> str:
        result = await self.generate_with_retry(prompt, system_prompt, model, temperature)
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
            async with httpx.AsyncClient(timeout=self.timeout) as client:
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

                logger.info(f"OpenAI generation successful: {total_tokens} tokens, {execution_time_ms}ms")

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
    """Anthropic Claude API provider with retry logic"""

    def __init__(self, api_key: Optional[str] = None, max_retries: int = None,
                 retry_delay: int = None, timeout: int = None):
        super().__init__(max_retries, retry_delay, timeout)
        self.api_key = api_key or settings.ANTHROPIC_API_KEY
        self.base_url = "https://api.anthropic.com/v1"
        self.max_retries = max_retries or settings.ANTHROPIC_MAX_RETRIES
        self.retry_delay = retry_delay or settings.ANTHROPIC_RETRY_DELAY
        self.timeout = timeout or settings.ANTHROPIC_TIMEOUT

    async def generate(self, prompt: str, system_prompt: Optional[str] = None,
                     model: Optional[str] = None, temperature: Optional[float] = None) -> str:
        result = await self.generate_with_retry(prompt, system_prompt, model, temperature)
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
            async with httpx.AsyncClient(timeout=self.timeout) as client:
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

                logger.info(f"Anthropic generation successful: {total_tokens} tokens, {execution_time_ms}ms")

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
    """Google Gemini API provider with retry logic"""

    def __init__(self, api_key: Optional[str] = None, max_retries: int = None,
                 retry_delay: int = None, timeout: int = None):
        super().__init__(max_retries, retry_delay, timeout)
        self.api_key = api_key or settings.GEMINI_API_KEY
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"
        self.max_retries = max_retries or settings.GEMINI_MAX_RETRIES
        self.retry_delay = retry_delay or settings.GEMINI_RETRY_DELAY
        self.timeout = timeout or settings.GEMINI_TIMEOUT

    async def generate(self, prompt: str, system_prompt: Optional[str] = None,
                     model: Optional[str] = None, temperature: Optional[float] = None) -> str:
        result = await self.generate_with_retry(prompt, system_prompt, model, temperature)
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
            async with httpx.AsyncClient(timeout=self.timeout) as client:
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

                logger.info(f"Gemini generation successful: {total_tokens} tokens, {execution_time_ms}ms")

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
    """Factory for creating AI provider instances with retry logic"""

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
        else:
            logger.warning(f"Unknown provider {provider_name}, defaulting to OpenAI")
            return OpenAIProvider(api_key)
