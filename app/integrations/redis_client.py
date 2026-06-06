"""
Redis Cache Integration

Manages Redis connection pool and provides dependency injection.
"""

from typing import Generator, Optional
from redis import Redis, ConnectionPool, RedisError

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


redis_pool: Optional[ConnectionPool] = None
redis_client: Optional[Redis] = None


def init_redis() -> None:
    """Initialize Redis connection pool"""
    global redis_pool, redis_client
    
    logger.info(f"Initializing Redis connection pool: {settings.REDIS_URL}")
    
    try:
        redis_pool = ConnectionPool.from_url(
            settings.REDIS_URL,
            max_connections=settings.REDIS_MAX_CONNECTIONS,
            socket_timeout=settings.REDIS_SOCKET_TIMEOUT,
            socket_connect_timeout=settings.REDIS_SOCKET_TIMEOUT,
            decode_responses=True,
        )
        
        redis_client = Redis(connection_pool=redis_pool)
        redis_client.ping()
        logger.info("Redis connection pool initialized successfully")
        
    except RedisError as e:
        logger.warning(f"Redis initialization failed: {e}. Cache will be unavailable.")
        redis_client = None


def close_redis() -> None:
    """Close Redis connection pool"""
    global redis_pool, redis_client
    
    if redis_pool:
        logger.info("Closing Redis connection pool")
        redis_pool.disconnect()
        redis_pool = None
        redis_client = None


def get_redis() -> Generator[Optional[Redis], None, None]:
    """
    FastAPI dependency for Redis client.
    
    Returns None if Redis is unavailable (graceful degradation).
    """
    yield redis_client


def get_redis_sync() -> Optional[Redis]:
    """Synchronous accessor for Redis client"""
    return redis_client


def check_redis_health() -> tuple[bool, str]:
    """Verify Redis connectivity"""
    if not redis_client:
        return False, "Redis client not initialized"
    
    try:
        redis_client.ping()
        return True, "Redis connection healthy"
    except RedisError as e:
        logger.error(f"Redis health check failed: {e}")
        return False, f"Redis unhealthy: {str(e)}"


def safe_redis_get(key: str, default: Optional[str] = None) -> Optional[str]:
    """Safely get value from Redis with fallback"""
    if not redis_client:
        return default
    
    try:
        return redis_client.get(key) or default
    except RedisError as e:
        logger.warning(f"Redis GET failed for key '{key}': {e}")
        return default


def safe_redis_set(key: str, value: str, ex: Optional[int] = None) -> bool:
    """Safely set value in Redis"""
    if not redis_client:
        return False
    
    try:
        redis_client.set(key, value, ex=ex)
        return True
    except RedisError as e:
        logger.warning(f"Redis SET failed for key '{key}': {e}")
        return False
