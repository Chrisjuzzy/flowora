import hashlib
import json
import time
from typing import Optional, Any

class CacheService:
    _instance = None
    
    def __init__(self):
        self._cache = {} # Simple in-memory cache for now (Key -> {value, expires_at})
    
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = CacheService()
        return cls._instance
    
    def _generate_key(self, prompt: str, system_prompt: str = None, model: str = None) -> str:
        content = f"{prompt}|{system_prompt}|{model}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def get(self, prompt: str, system_prompt: str = None, model: str = None) -> Optional[Any]:
        key = self._generate_key(prompt, system_prompt, model)
        entry = self._cache.get(key)
        
        if not entry:
            return None
            
        if time.time() > entry['expires_at']:
            del self._cache[key]
            return None
            
        return entry['value']
    
    def set(self, prompt: str, response: Any, system_prompt: str = None, model: str = None, ttl_seconds: int = 3600):
        key = self._generate_key(prompt, system_prompt, model)
        self._cache[key] = {
            'value': response,
            'expires_at': time.time() + ttl_seconds
        }
        
    def clear(self):
        self._cache = {}

cache_service = CacheService.get_instance()
