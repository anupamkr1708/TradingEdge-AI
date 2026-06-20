"""
Request Correlation Middleware

Generates and tracks correlation IDs for request tracing.
"""

import uuid
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware


class CorrelationMiddleware(BaseHTTPMiddleware):
    """
    Generate correlation ID for each request.
    
    Priority:
    1. X-Request-ID header (if provided by client/proxy)
    2. Generate new UUID
    
    Adds request_id to:
    - request.state for access in handlers
    - response headers for client tracking
    """
    
    async def dispatch(self, request: Request, call_next):
        # Extract or generate request ID
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        
        # Store in request state for logging
        request.state.request_id = request_id
        
        # Process request
        response = await call_next(request)
        
        # Add to response headers
        response.headers["X-Request-ID"] = request_id
        
        return response
