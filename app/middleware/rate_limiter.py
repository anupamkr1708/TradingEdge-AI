"""
Rate Limiting Middleware

Per-client rate limiting using Redis with configurable limits.
"""

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
import time

from app.integrations.redis_client import get_redis_sync
from app.core.logging import get_logger

logger = get_logger(__name__)


class RateLimiter(BaseHTTPMiddleware):
    """
    Token bucket rate limiter using Redis.
    
    Configuration per endpoint:
    - requests: max requests per window
    - window: time window in seconds
    """
    
    def __init__(self, app, limits: dict[str, dict] = None):
        super().__init__(app)
        self.limits = limits or {
            "/recommendations": {"requests": 30, "window": 60},  # 30 req/min
            "/recommendations/": {"requests": 30, "window": 60}
        }
    
    async def dispatch(self, request: Request, call_next):
        # Get client identifier
        client_id = self._get_client_id(request)
        
        # Check if endpoint is rate limited
        endpoint = self._normalize_path(request.url.path)
        limit_config = self._get_limit_config(endpoint)
        
        if not limit_config:
            return await call_next(request)
        
        # Check rate limit
        allowed, retry_after = self._check_rate_limit(
            client_id=client_id,
            endpoint=endpoint,
            requests=limit_config["requests"],
            window=limit_config["window"]
        )
        
        if not allowed:
            logger.warning(
                f"Rate limit exceeded: {client_id} on {endpoint}",
                extra={"client_id": client_id, "endpoint": endpoint}
            )
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Rate limit exceeded",
                    "code": "RATE_LIMIT_EXCEEDED",
                    "details": {
                        "retry_after": retry_after,
                        "limit": limit_config["requests"],
                        "window": limit_config["window"]
                    }
                },
                headers={"Retry-After": str(retry_after)}
            )
        
        return await call_next(request)
    
    def _get_client_id(self, request: Request) -> str:
        """Extract client identifier from request"""
        # Priority: API key > IP address
        api_key = request.headers.get("X-API-Key")
        if api_key:
            return f"key:{api_key}"
        
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return f"ip:{forwarded_for.split(',')[0].strip()}"
        
        return f"ip:{request.client.host if request.client else 'unknown'}"
    
    def _normalize_path(self, path: str) -> str:
        """Normalize path for matching"""
        # Remove trailing slash for consistency
        if path.endswith("/") and path != "/":
            path = path[:-1]
        
        # Match specific endpoints or patterns
        if path.startswith("/recommendations"):
            return "/recommendations"
        
        return path
    
    def _get_limit_config(self, endpoint: str) -> dict | None:
        """Get rate limit configuration for endpoint"""
        return self.limits.get(endpoint)
    
    def _check_rate_limit(
        self,
        client_id: str,
        endpoint: str,
        requests: int,
        window: int
    ) -> tuple[bool, int]:
        """
        Check if request is allowed under rate limit.
        
        Returns:
            (allowed, retry_after_seconds)
        """
        redis = get_redis_sync()
        if not redis:
            # Fail open if Redis unavailable
            logger.warning("Redis unavailable, skipping rate limit")
            return True, 0
        
        key = f"ratelimit:{client_id}:{endpoint}"
        now = int(time.time())
        
        try:
            # Get current count and TTL
            pipe = redis.pipeline()
            pipe.get(key)
            pipe.ttl(key)
            current_str, ttl = pipe.execute()
            
            current = int(current_str) if current_str else 0
            
            if current >= requests:
                # Rate limit exceeded
                retry_after = ttl if ttl > 0 else window
                return False, retry_after
            
            # Increment counter
            pipe = redis.pipeline()
            pipe.incr(key)
            if current == 0:
                # Set expiry on first request
                pipe.expire(key, window)
            pipe.execute()
            
            return True, 0
            
        except Exception as e:
            # Fail open on error
            logger.error(f"Rate limit check failed: {e}")
            return True, 0
