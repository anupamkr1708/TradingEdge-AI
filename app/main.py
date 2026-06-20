"""
TradeMind AI - FastAPI Application

Main application entry point with lifecycle management.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from starlette.responses import Response
import time

from app.core.config import settings
from app.core.logging import setup_logging, get_logger
from app.core.errors import (
    AppException,
    app_exception_handler,
    validation_exception_handler,
    global_exception_handler
)
from app.db.supabase import init_db, close_db
from app.integrations.redis_client import init_redis, close_redis
from app.middleware import RateLimiter, CorrelationMiddleware, SecurityHeadersMiddleware
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
        # Validate Groq API key
        if not settings.GROQ_API_KEY or settings.GROQ_API_KEY == "your_groq_api_key_here":
            raise ValueError("GROQ_API_KEY not configured in environment")
        logger.info("Groq API key validated")
        
        # Initialize database
        init_db()
        
        # Initialize Redis
        init_redis()
        
        logger.info("Application startup complete")
        
        yield
        
    except Exception as e:
        logger.error(f"Application startup failed: {e}", exc_info=True)
        raise
        
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

# Exception handlers
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(AppException, app_exception_handler)
app.add_exception_handler(Exception, global_exception_handler)

# Middleware (order matters: first added = outermost)
# 1. Security headers (outermost)
app.add_middleware(
    SecurityHeadersMiddleware,
    enable_hsts=(settings.ENVIRONMENT == "production")
)

# 2. CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 3. Correlation ID tracking
app.add_middleware(CorrelationMiddleware)

# 4. Rate limiting
app.add_middleware(RateLimiter)



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
    
    # Log slow requests
    request_id = getattr(request.state, "request_id", None)
    if latency > 1.0:
        logger.warning(
            f"Slow request: {request.method} {request.url.path} took {latency:.2f}s",
            extra={"request_id": request_id, "latency": latency}
        )
    
    return response


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
