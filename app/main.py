from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.api.v1 import auth, users
from app.core.config import settings
from app.core.logging import logger
from app.core.middleware import (
    HTTPSRedirectMiddleware,
    RequestLoggingMiddleware,
    SecurityHeadersMiddleware,
)
from app.core.rate_limit import limiter

app = FastAPI(
    title="Secure Auth Service",
    version="0.1.0",
    docs_url="/docs" if settings.DEBUG else None,  # Hide docs in production
    redoc_url="/redoc" if settings.DEBUG else None,
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Add security middleware (order matters!)
app.add_middleware(HTTPSRedirectMiddleware)  # First - redirect HTTP to HTTPS
app.add_middleware(SecurityHeadersMiddleware)  # Second - add security headers
app.add_middleware(RequestLoggingMiddleware)  # Third - log requests
app.add_middleware(SlowAPIMiddleware)  # Fourth - rate limiting


# Security Middleware
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["localhost", "127.0.0.1", "*"],  # Restrict in production
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:8000",
    ],  # Restrict origins
    allow_credentials=True,
    allow_methods=["GET", "POST"],  # Only allow needed methods
    allow_headers=["*"],
)


app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(users.router, prefix="/users", tags=["users"])


@app.get("/health")
async def health():
    logger.info("Health check requested")
    return {"status": "ok", "service": "secure-auth-service", "version": "0.1.0"}


# Log application startup
logger.info(f"Starting Secure Auth Service v0.1.0 - Debug mode: {settings.DEBUG}")
