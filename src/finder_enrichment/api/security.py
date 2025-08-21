"""
Security middleware and rate limiting for the orchestration FastAPI API.
"""
from typing import Callable

from fastapi import Request, Response
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from slowapi.middleware import SlowAPIMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

# Create rate limiter instance with a global default limit
# Adjust the default limit as needed
limiter = Limiter(key_func=get_remote_address, default_limits=["1000/minute"])


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware that adds security headers to all responses.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)

        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # Add HSTS header (only in production/HTTPS)
        if request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains"
            )

        return response


def setup_rate_limiting(app):
    """
    Setup rate limiting for the FastAPI application.
    Applies a global default limit to all routes via SlowAPIMiddleware.
    """

    # Add rate limiter to app state
    app.state.limiter = limiter

    # Add rate limit exceeded handler
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # Add the SlowAPI middleware to enforce limits globally
    app.add_middleware(SlowAPIMiddleware)


# Optional: Rate limit decorators for specific endpoints (not required when using global default limits)

def rate_limit_standard():
    """Standard rate limit: 1000 requests per minute per IP."""

    return limiter.limit("1000/minute")


def rate_limit_burst():
    """Burst rate limit: 200 requests per 10 seconds per IP."""

    return limiter.limit("200/10 seconds")


def rate_limit_strict():
    """Strict rate limit: 100 requests per minute per IP."""

    return limiter.limit("100/minute")


def rate_limit_backend():
    """Backend service rate limit: 2000 requests per minute per IP."""

    return limiter.limit("2000/minute") 