from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import httpx
from config_production import settings
from utils.logger import logger
import time
from .cache_service import cache_service
from services.ai_limiter import ollama_limiter
from services.ollama_service import post_ollama_json

class AIProvider(ABC):
    @abstractmethod
    async def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """Simple wrapper to return just text"""
        pass

    @abstractmethod
    async def generate_text(self, prompt: str, system_prompt: Optional[str] = None, model: Optional[str] = None, api_key: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate text from the AI provider asynchronously.
        Returns a dict with 'text', 'token_usage', 'execution_time_ms', 'cost_estimate'.
        """
        pass

class LocalProvider(AIProvider):
    def __init__(self, base_url: str = settings.OLLAMA_BASE_URL):
        self.base_url = base_url

    async def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        result = await self.generate_text(prompt, system_prompt)
        return result["text"]

    async def generate_text(self, prompt: str, system_prompt: Optional[str] = None, model: Optional[str] = None, api_key: Optional[str] = None) -> Dict[str, Any]:
        # 1. Check Cache
        cached_result = cache_service.get(prompt, system_prompt, model)
        if cached_result:
            logger.info(f"Cache Hit for prompt: {prompt[:30]}...")
            return cached_result

        start_time = time.time()
        url = f"{self.base_url}/api/generate"
        
        # Determine model
        model = model or settings.DEFAULT_AI_MODEL
        
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False
        }
        if system_prompt:
            payload["system"] = system_prompt
        
        async def _call():
            if self.base_url.rstrip("/") != settings.OLLAMA_BASE_URL.rstrip("/"):
                async with httpx.AsyncClient(timeout=settings.OLLAMA_TIMEOUT_SECONDS) as client:
                    response = await client.post(url, json=payload)
                    response.raise_for_status()
                    return response.json()
            return await post_ollama_json(
                path="/api/generate",
                json_body=payload,
                required_model=model,
                read_timeout=settings.OLLAMA_TIMEOUT_SECONDS,
            )

        try:
            data = await ollama_limiter.run(_call)

            end_time = time.time()
            execution_time_ms = int((end_time - start_time) * 1000)

            tokens = data.get("eval_count", 0) + data.get("prompt_eval_count", 0)

            result = {
                "text": data.get("response", ""),
                "token_usage": tokens,
                "execution_time_ms": execution_time_ms,
                "cost_estimate": "0.0"
            }
            # 2. Cache Result
            cache_service.set(prompt, result, system_prompt, model)
            return result
        except (httpx.RequestError, httpx.HTTPStatusError) as e:
            logger.error(
                "Local AI Request Error: %s",
                str(e),
                extra={"props": {"provider": "local", "error": str(e)}},
                exc_info=True
            )
            if not settings.ALLOW_LLM_MOCK_FALLBACK:
                raise RuntimeError(f"Ollama request failed: {e}")
            # Smart Mock Responses
            mock_text = f"[Mock LLM Response - Local Provider Unavailable] processed: {prompt[:50]}..."
            
            if "JSON list of strings" in prompt:
                mock_text = '["Research competitors", "Draft content strategy", "Set up analytics", "Launch campaign"]'
            elif "JSON list of objects" in prompt:
                mock_text = '[{"title": "AI Personal Shopper", "description": "Automated shopping assistant", "type": "business_idea", "confidence": 0.85}, {"title": "Code Review Bot", "description": "Auto-fix pull requests", "type": "automation", "confidence": 0.92}]'
            elif "Predict the outcome" in prompt:
                mock_text = "Outcome: The customer will likely be satisfied if responded to promptly.\nScore: 85"
            elif "suggest one proactive optimization" in prompt:
                mock_text = "Suggestion: Automate your daily report generation to save 30 minutes each morning."
            elif "Fix the following python code" in prompt:
                mock_text = """The code has a syntax error. The closing parenthesis is missing.
Here is the fixed code:
```python
print("hello")
```
Explanation: The `print` function in Python 3 requires parentheses around the argument."""

            result = {
                "text": mock_text,
                "token_usage": 0,
                "execution_time_ms": 0,
                "cost_estimate": "0.0",
                "mock": True
            }
            # Cache the mock response too
            cache_service.set(prompt, result, system_prompt, model)
            return result
        except Exception as e:
            logger.error(f"Local AI Error: {str(e)}", extra={"props": {"provider": "local", "error": str(e)}})
            raise e

class OpenAIProvider(AIProvider):
    async def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        result = await self.generate_text(prompt, system_prompt)
        return result["text"]

    async def generate_text(self, prompt: str, system_prompt: Optional[str] = None, model: Optional[str] = "gpt-3.5-turbo", api_key: Optional[str] = None) -> Dict[str, Any]:
        # Placeholder implementation with simulated usage
        
        # Estimate tokens (approx 4 chars per token)
        input_tokens = len(prompt) // 4
        output_tokens = 50 # Mock output length
        total_tokens = input_tokens + output_tokens
        
        # Mock Cost: $0.002 per 1k tokens (approx gpt-3.5 price)
        cost = (total_tokens / 1000) * 0.002
        
        return {
            "text": f"[OpenAI Response to: {prompt[:20]}...]",
            "token_usage": total_tokens,
            "execution_time_ms": 500,
            "cost_estimate": f"{cost:.6f}"
        }

class FallbackProvider(AIProvider):
    def __init__(self, primary: AIProvider, secondary: AIProvider):
        self.primary = primary
        self.secondary = secondary

    async def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        try:
            return await self.primary.generate(prompt, system_prompt)
        except Exception as e:
            logger.warning(f"Primary provider failed, switching to secondary: {e}")
            return await self.secondary.generate(prompt, system_prompt)

    async def generate_text(self, prompt: str, system_prompt: Optional[str] = None, model: Optional[str] = None, api_key: Optional[str] = None) -> Dict[str, Any]:
        try:
            return await self.primary.generate_text(prompt, system_prompt, model, api_key)
        except Exception as e:
            logger.warning(f"Primary provider failed, switching to secondary: {e}")
            return await self.secondary.generate_text(prompt, system_prompt, model, api_key)

class HybridOrchestrator(AIProvider):
    """
    Intelligent router that balances cost, latency, and capability.
    - Local LLM: First choice for simple/medium tasks (low cost).
    - Cloud LLM: Fallback for complex tasks or when local is overloaded.
    """
    def __init__(self, local: AIProvider, cloud: AIProvider):
        self.local = local
        self.cloud = cloud
        self.cost_threshold = 0.01 # Max cost per request preference
        self.complexity_keywords = ["reasoning", "complex", "analysis", "creative", "strategy"]

    async def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        result = await self.generate_text(prompt, system_prompt)
        return result["text"]

    async def generate_text(self, prompt: str, system_prompt: Optional[str] = None, model: Optional[str] = None, api_key: Optional[str] = None) -> Dict[str, Any]:
        # 1. Complexity Check
        is_complex = any(k in prompt.lower() for k in self.complexity_keywords) or len(prompt) > 1000
        
        # 2. Routing Logic
        if is_complex and model != "local":
            logger.info("Routing to Cloud Provider (Complexity detected)")
            try:
                return await self.cloud.generate_text(prompt, system_prompt, model, api_key)
            except Exception as e:
                logger.warning(f"Cloud provider failed, falling back to local: {e}")
                return await self.local.generate_text(prompt, system_prompt, model, api_key)
        else:
            logger.info("Routing to Local Provider (Cost optimization)")
            try:
                return await self.local.generate_text(prompt, system_prompt, model, api_key)
            except Exception as e:
                logger.warning(f"Local provider failed, falling back to cloud: {e}")
                return await self.cloud.generate_text(prompt, system_prompt, model, api_key)

class AIProviderFactory:
    @staticmethod
    def get_provider(provider_name: str = settings.DEFAULT_AI_PROVIDER) -> AIProvider:
        local_p = LocalProvider()
        openai_p = OpenAIProvider()
        
        # Default strategy: Hybrid Orchestration
        if provider_name == "hybrid":
            return HybridOrchestrator(local=local_p, cloud=openai_p)
        elif provider_name == "openai":
            return FallbackProvider(openai_p, local_p)
        elif provider_name == "local":
            return local_p
        else:
            return HybridOrchestrator(local=local_p, cloud=openai_p)

# Global instance
ai_service = AIProviderFactory.get_provider("hybrid")
