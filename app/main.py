"""
TradeMind AI - FastAPI Application

Main application entry point with lifecycle management.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from starlette.responses import Response
import time

from app.core.config import settings
from app.core.logging import setup_logging, get_logger
from app.db.supabase import init_db, close_db
from app.integrations.redis_client import init_redis, close_redis
from app.routers import health
from app.monitoring.metrics import metrics

# Setup logging before anything else
setup_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle"""
    
    # Startup
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    
    try:
        # Initialize database
        init_db()
        
        # Initialize Redis
        init_redis()
        
        logger.info("Application startup complete")
        
        yield
        
    finally:
        # Shutdown
        logger.info("Shutting down application")
        close_redis()
        close_db()
        logger.info("Application shutdown complete")


# Create FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AI-powered trading intelligence platform",
    lifespan=lifespan,
)


# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request timing middleware
@app.middleware("http")
async def add_metrics_middleware(request: Request, call_next):
    """Record API metrics for each request"""
    start_time = time.time()
    
    response = await call_next(request)
    
    latency = time.time() - start_time
    
    # Record metrics
    metrics.record_api_request(
        method=request.method,
        endpoint=request.url.path,
        status_code=response.status_code
    )
    metrics.record_api_latency(
        endpoint=request.url.path,
        latency_seconds=latency
    )
    
    return response


# Exception handlers
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler"""
    logger.error(
        f"Unhandled exception: {exc}",
        exc_info=True,
        extra={"context": {"path": request.url.path, "method": request.method}}
    )
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "detail": str(exc)}
    )


# Include routers
app.include_router(health.router)

# Import and include recommendations router
from app.routers import recommendations
app.include_router(recommendations.router)


# Prometheus metrics endpoint
@app.get("/metrics", include_in_schema=False)
def prometheus_metrics():
    """Expose metrics for Prometheus scraping"""
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )


# Root endpoint
@app.get("/")
def root():
    """API root endpoint"""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "status": "operational"
    }
