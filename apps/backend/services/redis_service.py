
"""
Redis Service - Caching and session management for Flowora
Handles rate limiting, session caching, and task queues
"""
import json
import logging
import time
import uuid
from typing import Optional, Any, Dict, List
from datetime import timedelta
import redis
from config_production import settings

logger = logging.getLogger(__name__)

# Redis client instance
redis_client = None


def get_redis_client():
    """Get or create Redis client instance with graceful failure handling"""
    global redis_client

    if redis_client is None:
        try:
            redis_client = redis.Redis(
                host=settings.REDIS_URL.split('://')[1].split(':')[0],
                port=int(settings.REDIS_URL.split(':')[2].split('/')[0]),
                db=int(settings.REDIS_URL.split('/')[-1]),
                max_connections=settings.REDIS_MAX_CONNECTIONS,
                socket_timeout=settings.REDIS_SOCKET_TIMEOUT,
                socket_connect_timeout=settings.REDIS_SOCKET_CONNECT_TIMEOUT,
                decode_responses=settings.REDIS_DECODE_RESPONSES,
                retry_on_timeout=True,
                health_check_interval=30
            )

            # Test connection
            redis_client.ping()
            logger.info("Redis client created successfully")

        except Exception as e:
            logger.warning(f"Failed to create Redis client: {e}")
            logger.warning("Application will run without Redis caching")
            redis_client = None

    return redis_client


class RedisCache:
    """Redis cache operations with graceful degradation"""

    def __init__(self):
        self.client = get_redis_client()
        self.redis_available = self.client is not None

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        if not self.redis_available:
            return None
        try:
            value = self.client.get(key)
            if value:
                try:
                    return json.loads(value)
                except json.JSONDecodeError:
                    return value.decode('utf-8')
            return None
        except Exception as e:
            logger.error(f"Cache get error for key {key}: {e}")
            return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache with optional TTL"""
        try:
            if isinstance(value, (dict, list)):
                value = json.dumps(value)
            elif not isinstance(value, (str, bytes)):
                value = str(value)

            if ttl:
                return self.client.setex(key, ttl, value)
            else:
                return self.client.set(key, value)
        except Exception as e:
            logger.error(f"Cache set error for key {key}: {e}")
            return False

    def delete(self, key: str) -> bool:
        """Delete key from cache"""
        try:
            return bool(self.client.delete(key))
        except Exception as e:
            logger.error(f"Cache delete error for key {key}: {e}")
            return False

    def exists(self, key: str) -> bool:
        """Check if key exists in cache"""
        try:
            return bool(self.client.exists(key))
        except Exception as e:
            logger.error(f"Cache exists error for key {key}: {e}")
            return False

    def expire(self, key: str, ttl: int) -> bool:
        """Set TTL for existing key"""
        try:
            return bool(self.client.expire(key, ttl))
        except Exception as e:
            logger.error(f"Cache expire error for key {key}: {e}")
            return False


class RateLimiter:
    """Rate limiting using Redis"""

    def __init__(self):
        self.client = get_redis_client()

    def is_allowed(self, key: str, limit: int, window: int = 60) -> Dict[str, Any]:
        """
        Check if request is allowed under rate limit

        Args:
            key: Unique identifier (e.g., user_id or IP)
            limit: Maximum number of requests
            window: Time window in seconds (default: 60)

        Returns:
            Dict with:
                - allowed: bool
                - remaining: int
                - reset_time: int
        """
        try:
            current_time = int(time.time())
            window_key = f"rate_limit:{key}"

            # Clean up old entries
            self.client.zremrangebyscore(window_key, 0, current_time - window)

            # Count current requests
            current_count = self.client.zcard(window_key)

            if current_count < limit:
                # Add current request
                self.client.zadd(window_key, {str(current_time): current_time})
                self.client.expire(window_key, window)

                return {
                    "allowed": True,
                    "remaining": limit - current_count - 1,
                    "reset_time": current_time + window
                }
            else:
                # Get reset time
                oldest_request = self.client.zrange(window_key, 0, 0, withscores=True)
                reset_time = int(oldest_request[0][1]) + window if oldest_request else current_time + window

                return {
                    "allowed": False,
                    "remaining": 0,
                    "reset_time": reset_time
                }

        except Exception as e:
            logger.error(f"Rate limiter error for key {key}: {e}")
            # Fail open - allow request if rate limiter fails
            return {
                "allowed": True,
                "remaining": limit,
                "reset_time": int(time.time()) + window
            }


class SessionManager:
    """Session management using Redis"""

    def __init__(self):
        self.client = get_redis_client()
        self.cache = RedisCache()

    def create_session(self, user_id: int, session_data: Dict[str, Any], ttl: int = 3600) -> str:
        """
        Create a new session

        Args:
            user_id: User ID
            session_data: Session data to store
            ttl: Time to live in seconds (default: 1 hour)

        Returns:
            Session ID
        """
        try:
            session_id = f"session:{user_id}:{uuid.uuid4().hex}"
            self.cache.set(session_id, session_data, ttl)
            return session_id
        except Exception as e:
            logger.error(f"Session creation error for user {user_id}: {e}")
            raise

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session data"""
        return self.cache.get(session_id)

    def update_session(self, session_id: str, session_data: Dict[str, Any], ttl: Optional[int] = None) -> bool:
        """Update session data"""
        return self.cache.set(session_id, session_data, ttl)

    def delete_session(self, session_id: str) -> bool:
        """Delete session"""
        return self.cache.delete(session_id)

    def extend_session(self, session_id: str, ttl: int = 3600) -> bool:
        """Extend session TTL"""
        return self.cache.expire(session_id, ttl)


# Global instances (initialized lazily to handle connection errors)
cache = None
rate_limiter = None

def get_cache() -> RedisCache:
    """Get cache instance, creating if needed"""
    global cache
    if cache is None:
        cache = RedisCache()
    return cache

def get_rate_limiter() -> RateLimiter:
    """Get rate limiter instance, creating if needed"""
    global rate_limiter
    if rate_limiter is None:
        rate_limiter = RateLimiter()
    return rate_limiter
session_manager = SessionManager()
