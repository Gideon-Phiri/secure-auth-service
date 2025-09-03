"""
Security middleware for the application.
Handles security headers, HTTPS enforcement, and other security-related middleware.
"""
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import RedirectResponse
from app.core.config import settings
import time
import uuid


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses."""
    
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # Security Headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # Content Security Policy (restrictive for API)
        response.headers["Content-Security-Policy"] = (
            "default-src 'none'; "
            "script-src 'self'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; "
            "connect-src 'self'; "
            "font-src 'self'; "
            "frame-ancestors 'none'"
        )
        
        # Only add HSTS in production and when using HTTPS
        if not settings.DEBUG and request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
        
        # Server header (hide server info)
        response.headers["Server"] = "SecureAuthService"
        
        return response


class HTTPSRedirectMiddleware(BaseHTTPMiddleware):
    """Redirect HTTP to HTTPS in production."""
    
    async def dispatch(self, request: Request, call_next):
        # Only enforce HTTPS in production
        if (not settings.DEBUG and 
            request.url.scheme == "http" and 
            request.method in ["GET", "HEAD"]):
            
            # Build HTTPS URL
            https_url = request.url.replace(scheme="https")
            return RedirectResponse(url=str(https_url), status_code=301)
        
        return await call_next(request)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log requests for monitoring and security."""
    
    async def dispatch(self, request: Request, call_next):
        # Generate request ID for tracing
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        start_time = time.time()
        
        # Log request start
        from app.core.logging import logger
        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent", "unknown")
        
        logger.info(
            f"REQUEST {request_id}: {request.method} {request.url.path} "
            f"from {client_ip} - {user_agent}"
        )
        
        response = await call_next(request)
        
        # Calculate request duration
        duration = time.time() - start_time
        
        # Log request completion
        logger.info(
            f"RESPONSE {request_id}: {response.status_code} in {duration:.3f}s"
        )
        
        # Add request ID to response headers for debugging
        response.headers["X-Request-ID"] = request_id
        
        return response
