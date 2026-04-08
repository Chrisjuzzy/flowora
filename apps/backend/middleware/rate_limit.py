from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request
from fastapi.responses import JSONResponse
import time
from collections import defaultdict
from jose import JWTError, jwt
from config_production import settings
from services.redis_service import get_rate_limiter
import logging

logger = logging.getLogger(__name__)

class RateLimiter:
    def __init__(self):
        self._redis = get_rate_limiter()
        self._tokens = defaultdict(lambda: settings.RATE_LIMIT_API_PER_MINUTE * 2)
        self._last_refill = defaultdict(lambda: time.time())

    def _local_allow(self, key: str, limit: int, window: int, burst_limit: int) -> bool:
        now = time.time()
        time_passed = now - self._last_refill[key]
        refill_rate = limit / window
        tokens_to_add = time_passed * refill_rate
        self._tokens[key] = min(burst_limit, self._tokens[key] + tokens_to_add)
        self._last_refill[key] = now
        if self._tokens[key] >= 1:
            self._tokens[key] -= 1
            return True
        return False

    def is_allowed(self, key: str, limit: int, window: int, burst_limit: int) -> bool:
        if self._redis and getattr(self._redis, "client", None):
            result = self._redis.is_allowed(key, limit=limit, window=window)
            return bool(result.get("allowed", True))
        return self._local_allow(key, limit, window, burst_limit)

class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, limit: int = settings.RATE_LIMIT_API_PER_MINUTE, window: int = 60):
        super().__init__(app)
        self.limit = limit
        self.window = window
        self.limiter = RateLimiter()

    def _resolve_limit(self, path: str) -> int:
        if path.startswith("/auth"):
            return settings.RATE_LIMIT_AUTH_PER_MINUTE
        if path.startswith("/agents/") and path.endswith("/run"):
            return settings.RATE_LIMIT_EXECUTION_PER_MINUTE
        if path.startswith("/workflows/") and path.endswith("/run"):
            return settings.RATE_LIMIT_WORKFLOW_PER_MINUTE
        return self.limit

    def _resolve_identity(self, request: Request) -> dict:
        auth_header = request.headers.get("Authorization", "")
        api_key = request.headers.get("X-API-Key", "")
        if auth_header.lower().startswith("bearer "):
            token = auth_header.split(" ", 1)[1]
            try:
                payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
                sub = payload.get("sub")
                if sub:
                    return {"key": f"user:{sub}", "user_id": sub, "api_key": None, "ip": request.client.host if request.client else None}
            except JWTError:
                pass
        if api_key:
            return {"key": f"api_key:{api_key[:8]}", "user_id": None, "api_key": api_key[:8], "ip": request.client.host if request.client else None}
        if request.client:
            return {"key": f"ip:{request.client.host}", "user_id": None, "api_key": None, "ip": request.client.host}
        return {"key": "anonymous", "user_id": None, "api_key": None, "ip": None}

    def _log_block(self, request: Request, identity: dict, reason: str, limit: int) -> None:
        logger.warning(
            "Rate limit blocked request",
            extra={
                "path": request.url.path,
                "method": request.method,
                "key": identity.get("key"),
                "user_id": identity.get("user_id"),
                "ip": identity.get("ip"),
                "reason": reason,
                "limit": limit
            }
        )

    async def dispatch(self, request: Request, call_next):
        if not settings.RATE_LIMIT_ENABLED:
            return await call_next(request)

        identity = self._resolve_identity(request)
        key = identity["key"]
        limit = self._resolve_limit(request.url.path)
        burst_limit = max(limit * 2, 1)

        if not self.limiter.is_allowed(key, limit=limit, window=self.window, burst_limit=burst_limit):
            self._log_block(request, identity, "path_limit", limit)
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded. Please try again later."}
            )

        if identity.get("user_id") and settings.RATE_LIMIT_USER_PER_MINUTE:
            user_key = f"user_global:{identity['user_id']}"
            user_limit = settings.RATE_LIMIT_USER_PER_MINUTE
            user_burst = max(user_limit * 2, 1)
            if not self.limiter.is_allowed(user_key, limit=user_limit, window=self.window, burst_limit=user_burst):
                self._log_block(request, identity, "user_throttle", user_limit)
                return JSONResponse(
                    status_code=429,
                    content={"detail": "User request throttled. Please slow down."}
                )

        response = await call_next(request)
        return response
