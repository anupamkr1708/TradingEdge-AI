"""
Health Check Endpoints

Provides liveness, readiness, and comprehensive health checks.
"""

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from redis import Redis
from datetime import datetime

from app.db.supabase import get_db, check_database_health
from app.integrations.redis_client import get_redis, check_redis_health
from app.monitoring.metrics import metrics
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(tags=["Health"])


@router.get("/health")
async def health_check(
    db: Session = Depends(get_db),
    redis: Redis = Depends(get_redis)
):
    """
    Comprehensive health check of all dependencies.
    Returns 200 if all healthy, 503 if any critical service down.
    """
    
    health = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "services": {}
    }
    
    # Check Supabase
    db_healthy, db_message = check_database_health()
    health["services"]["supabase"] = {
        "status": "healthy" if db_healthy else "unhealthy",
        "message": db_message
    }
    metrics.update_health_status("supabase", db_healthy)
    
    if not db_healthy:
        health["status"] = "unhealthy"
    
    # Check Redis
    redis_healthy, redis_message = check_redis_health()
    health["services"]["redis"] = {
        "status": "healthy" if redis_healthy else "unhealthy",
        "message": redis_message
    }
    metrics.update_health_status("redis", redis_healthy)
    
    if not redis_healthy:
        health["status"] = "degraded"  # Non-critical
    
    status_code = 200 if health["status"] in ["healthy", "degraded"] else 503
    
    return JSONResponse(content=health, status_code=status_code)


@router.get("/health/live")
def liveness_probe():
    """
    Kubernetes liveness probe.
    Returns 200 if process is running.
    """
    return {"status": "alive", "timestamp": datetime.utcnow().isoformat() + "Z"}


@router.get("/health/ready")
async def readiness_probe(db: Session = Depends(get_db)):
    """
    Kubernetes readiness probe.
    Returns 200 if ready to accept traffic, 503 otherwise.
    """
    db_healthy, message = check_database_health()
    
    if db_healthy:
        return {"status": "ready", "timestamp": datetime.utcnow().isoformat() + "Z"}
    else:
        return JSONResponse(
            content={"status": "not_ready", "message": message},
            status_code=503
        )
