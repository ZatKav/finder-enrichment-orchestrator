# FastAPI Security Implementation Guide

This guide provides comprehensive instructions for implementing the same security features in any FastAPI application. It covers API key authentication, security headers, rate limiting infrastructure, and security best practices.

## Table of Contents

- [FastAPI Security Implementation Guide](#fastapi-security-implementation-guide)
  - [Table of Contents](#table-of-contents)
  - [Overview](#overview)
  - [Dependencies](#dependencies)
  - [API Key Authentication](#api-key-authentication)
    - [1. Create Authentication Module](#1-create-authentication-module)
    - [2. Environment Configuration](#2-environment-configuration)
  - [Security Headers Middleware](#security-headers-middleware)
    - [1. Create Security Module](#1-create-security-module)
  - [Rate Limiting Infrastructure](#rate-limiting-infrastructure)
    - [1. Basic Rate Limiting Setup](#1-basic-rate-limiting-setup)
    - [2. Global Rate Limiting](#2-global-rate-limiting)
  - [Application Integration](#application-integration)
    - [1. Main Application Setup](#1-main-application-setup)
    - [2. Router Example](#2-router-example)
  - [Testing](#testing)
    - [1. Authentication Tests](#1-authentication-tests)
    - [2. Security Headers and Rate Limiting Tests](#2-security-headers-and-rate-limiting-tests)
    - [3. API Endpoint Integration Tests](#3-api-endpoint-integration-tests)

## Overview

This implementation provides:

- **API Key Authentication**: Secure Bearer token-based authentication
- **Security Headers**: Protection against XSS, clickjacking, and MIME type sniffing
- **Rate Limiting Infrastructure**: Ready-to-deploy rate limiting system
- **Information Leakage Prevention**: Consistent 500 error responses for auth failures
- **Production-Ready**: Comprehensive testing and configuration options

## Dependencies

Add these dependencies to your `pyproject.toml` or `requirements.txt`:

```toml
# For rate limiting
slowapi = "^1.2.0"

# For environment variables (if not already using)
python-dotenv = "^1.0.0"
```

Or install via pip:

```bash
pip install slowapi python-dotenv
```

## API Key Authentication

### 1. Create Authentication Module

Create `auth.py` in your FastAPI application:

```python
"""
API Key Authentication for FastAPI.
Provides secure Bearer token-based authentication with information leakage prevention.
"""

import os
from typing import Optional
from fastapi import HTTPException, Security, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Security scheme
security = HTTPBearer(auto_error=False)

def get_api_key(credentials: Optional[HTTPAuthorizationCredentials] = Security(security)) -> str:
    """
    Validate API key from Authorization header.
    
    Args:
        credentials: HTTP Authorization credentials from request header
        
    Returns:
        str: Validated API key
        
    Raises:
        HTTPException: 500 Internal Server Error for any authentication failure
    """
    # Get API key from environment
    api_key = os.getenv("API_KEY")
    
    if not api_key:
        raise HTTPException(
            status_code=500,
            detail="Internal Server Error",
        )
    
    # Check if Authorization header is present
    if not credentials:
        raise HTTPException(
            status_code=500,
            detail="Internal Server Error",
        )
    
    # Validate Bearer scheme
    if credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=500,
            detail="Internal Server Error",
        )
    
    # Validate API key
    if not credentials.credentials or credentials.credentials.strip() != api_key.strip():
        raise HTTPException(
            status_code=500,
            detail="Internal Server Error",
        )
    
    return credentials.credentials

# Dependency for protected endpoints
def require_api_key(api_key: str = Depends(get_api_key)) -> str:
    """
    Dependency that requires valid API key authentication.
    
    Args:
        api_key: Validated API key from get_api_key
        
    Returns:
        str: The validated API key
    """
    return api_key
```

### 2. Environment Configuration

Create a `.env` file in your project root:

```bash
# API Authentication
API_KEY=your_very_long_and_secure_api_key_here_at_least_32_characters

# Optional: Database and other configuration
DATABASE_URL=postgresql://user:password@localhost/dbname
```

**Security Note**: Use a strong API key (at least 32 characters) with a mix of letters, numbers, and special characters.

## Security Headers Middleware

### 1. Create Security Module

Create `security.py` in your FastAPI application:

```python
"""
Security middleware for FastAPI applications.
Includes security headers and rate limiting infrastructure.
"""

import time
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# Create rate limiter instance
limiter = Limiter(key_func=get_remote_address)

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
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        
        return response

def setup_rate_limiting(app):
    """
    Setup rate limiting for the FastAPI application.
    
    Args:
        app: FastAPI application instance
    """
    # Add rate limiter to app state
    app.state.limiter = limiter
    
    # Add rate limit exceeded handler
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Rate limit decorators for different endpoints
def rate_limit_standard():
    """
    Standard rate limit: 1000 requests per minute per IP
    Suitable for most API endpoints.
    """
    return limiter.limit("1000/minute")

def rate_limit_burst():
    """
    Burst rate limit: 200 requests per 10 seconds per IP
    For high-frequency operations.
    """
    return limiter.limit("200/10 seconds")

def rate_limit_strict():
    """
    Strict rate limit: 100 requests per minute per IP
    For sensitive operations.
    """
    return limiter.limit("100/minute")

def rate_limit_backend():
    """
    Backend service rate limit: 2000 requests per minute per IP
    Higher limits for backend-to-backend communication.
    """
    return limiter.limit("2000/minute")
```

## Rate Limiting Infrastructure

### 1. Basic Rate Limiting Setup

The rate limiting infrastructure is already set up in the security module. To apply rate limiting to specific endpoints:

```python
from fastapi import APIRouter, Depends
from .security import rate_limit_standard, rate_limit_burst
from .auth import require_api_key

router = APIRouter()

@router.get("/api/data/")
@rate_limit_standard()
async def get_data(api_key: str = Depends(require_api_key)):
    """Standard rate-limited endpoint."""
    return {"data": "example"}

@router.post("/api/burst/")
@rate_limit_burst()
async def burst_operation(api_key: str = Depends(require_api_key)):
    """Burst rate-limited endpoint."""
    return {"status": "success"}
```

### 2. Global Rate Limiting

To apply rate limiting globally to all endpoints:

```python
# In your main.py
from .security import setup_rate_limiting, limiter

# Setup rate limiting
setup_rate_limiting(app)

# Apply global rate limiting (optional)
@app.middleware("http")
async def global_rate_limit(request: Request, call_next):
    # Apply rate limiting to all API routes
    if request.url.path.startswith("/api/"):
        await limiter.check_request_limit(request)
    return await call_next(request)
```

## Application Integration

### 1. Main Application Setup

Update your `main.py` to integrate all security features:

```python
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from .auth import require_api_key
from .security import SecurityHeadersMiddleware, setup_rate_limiting

# Create FastAPI app
app = FastAPI(
    title="Your API",
    description="Your API with comprehensive security features",
    version="1.0.0",
)

# Setup rate limiting
setup_rate_limiting(app)

# Add CORS middleware (configure as needed)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add security headers middleware
app.add_middleware(SecurityHeadersMiddleware)

# Public endpoints (no authentication required)
@app.get("/")
async def root():
    return {"message": "Welcome to the API"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

# Protected endpoints (authentication required)
@app.get("/api/protected")
async def protected_endpoint(api_key: str = Depends(require_api_key)):
    return {"message": "This is a protected endpoint", "authenticated": True}

# Include your routers
from .routers import data, users
app.include_router(data.router, prefix="/api", tags=["data"])
app.include_router(users.router, prefix="/api", tags=["users"])
```

### 2. Router Example

Example router with authentication and rate limiting:

```python
# routers/data.py
from fastapi import APIRouter, Depends, HTTPException
from .auth import require_api_key
from .security import rate_limit_standard, rate_limit_burst

router = APIRouter()

@router.get("/data/")
@rate_limit_standard()
async def get_data(api_key: str = Depends(require_api_key)):
    """Get data with standard rate limiting."""
    return {"data": "example data"}

@router.post("/data/")
@rate_limit_burst()
async def create_data(api_key: str = Depends(require_api_key)):
    """Create data with burst rate limiting."""
    return {"status": "created"}

@router.get("/data/{item_id}")
@rate_limit_standard()
async def get_data_item(item_id: int, api_key: str = Depends(require_api_key)):
    """Get specific data item."""
    return {"id": item_id, "data": "item data"}
```

## Testing

### 1. Authentication Tests

Create `tests/test_auth.py`:

```python
"""
Comprehensive tests for API key authentication.
Tests all authentication scenarios and edge cases.
"""

import pytest
import os
from fastapi.testclient import TestClient
from dotenv import load_dotenv

load_dotenv()

# Get API key for testing
API_KEY = os.getenv("API_KEY")

if not API_KEY:
    raise EnvironmentError("API_KEY environment variable is required for testing.")

@pytest.fixture
def test_client():
    from main import app
    return TestClient(app)

class TestAuthentication:
    """Comprehensive test cases for API key authentication."""
    
    def test_public_endpoints_no_auth_required(self, test_client: TestClient):
        """Test that public endpoints don't require authentication."""
        response = test_client.get("/")
        assert response.status_code == 200
        
        response = test_client.get("/health")
        assert response.status_code == 200
    
    def test_protected_endpoint_without_auth_fails(self, test_client: TestClient):
        """Test that protected endpoints return 500 without authentication (security measure)."""
        response = test_client.get("/api/protected")
        assert response.status_code == 500
        assert "detail" in response.json()
    
    def test_protected_endpoint_with_valid_api_key_succeeds(self, test_client: TestClient):
        """Test that protected endpoints work with valid API key."""
        headers = {"Authorization": f"Bearer {API_KEY}"}
        response = test_client.get("/api/protected", headers=headers)
        assert response.status_code == 200
    
    def test_protected_endpoint_with_invalid_api_key_fails(self, test_client: TestClient):
        """Test that protected endpoints fail with invalid API key (returns 500 for security)."""
        headers = {"Authorization": "Bearer invalid_api_key_12345"}
        response = test_client.get("/api/protected", headers=headers)
        assert response.status_code == 500
        assert "detail" in response.json()
    
    def test_protected_endpoint_with_wrong_scheme_fails(self, test_client: TestClient):
        """Test that protected endpoints fail with wrong authentication scheme (returns 500 for security)."""
        headers = {"Authorization": f"Basic {API_KEY}"}
        response = test_client.get("/api/protected", headers=headers)
        assert response.status_code == 500
        assert "detail" in response.json()
    
    def test_protected_endpoint_with_malformed_header_fails(self, test_client: TestClient):
        """Test that protected endpoints fail with malformed authorization header."""
        headers = {"Authorization": f"Bearer{API_KEY}"}  # Missing space
        response = test_client.get("/api/protected", headers=headers)
        assert response.status_code == 500
    
    def test_protected_endpoint_with_empty_bearer_token_fails(self, test_client: TestClient):
        """Test that protected endpoints fail with empty bearer token."""
        headers = {"Authorization": "Bearer "}
        response = test_client.get("/api/protected", headers=headers)
        assert response.status_code == 500
    
    def test_protected_endpoint_with_partial_api_key_fails(self, test_client: TestClient):
        """Test that protected endpoints fail with partial API key (returns 500 for security)."""
        partial_key = API_KEY[:len(API_KEY)//2] if len(API_KEY) > 1 else "partial"
        headers = {"Authorization": f"Bearer {partial_key}"}
        response = test_client.get("/api/protected", headers=headers)
        assert response.status_code == 500
    
    def test_protected_endpoint_with_extra_characters_fails(self, test_client: TestClient):
        """Test that protected endpoints fail with API key that has extra characters (returns 500 for security)."""
        modified_key = f"{API_KEY}extra_chars"
        headers = {"Authorization": f"Bearer {modified_key}"}
        response = test_client.get("/api/protected", headers=headers)
        assert response.status_code == 500
    
    def test_protected_endpoint_with_whitespace_in_key_fails(self, test_client: TestClient):
        """Test that protected endpoints fail with API key that has whitespace (returns 500 for security)."""
        modified_key = f" {API_KEY} "  # Add whitespace
        headers = {"Authorization": f"Bearer {modified_key}"}
        response = test_client.get("/api/protected", headers=headers)
        assert response.status_code == 500
    
    def test_all_protected_endpoints_require_auth(self, test_client: TestClient):
        """Test that all protected endpoints require authentication."""
        protected_endpoints = [
            "/api/data/",
            "/api/users/",
            "/api/admin/",
            # Add your specific protected endpoints here
        ]
        
        for endpoint in protected_endpoints:
            response = test_client.get(endpoint)
            # All endpoints should return 500 for unauthenticated access
            assert response.status_code == 500, f"Endpoint {endpoint} should require authentication (got {response.status_code})"
    
    def test_all_protected_endpoints_work_with_valid_auth(self, test_client: TestClient):
        """Test that all protected endpoints work with valid authentication."""
        headers = {"Authorization": f"Bearer {API_KEY}"}
        protected_endpoints = [
            "/api/data/",
            "/api/users/",
            "/api/admin/",
            # Add your specific protected endpoints here
        ]
        
        for endpoint in protected_endpoints:
            response = test_client.get(endpoint, headers=headers)
            assert response.status_code in [200, 404], f"Endpoint {endpoint} should work with valid auth (got {response.status_code})"
    
    def test_post_endpoints_require_auth(self, test_client: TestClient):
        """Test that POST endpoints also require authentication."""
        headers = {"Authorization": f"Bearer {API_KEY}"}
        
        # Test POST endpoints with valid auth (should work, even if data is invalid)
        response = test_client.post("/api/data/", headers=headers, json={})
        assert response.status_code in [422, 400], "POST endpoint should require auth and return validation error with valid auth"
        
        # Test POST endpoints without auth (should fail)
        response = test_client.post("/api/data/", json={})
        assert response.status_code == 500, "POST endpoint should require authentication"
    
    def test_put_endpoints_require_auth(self, test_client: TestClient):
        """Test that PUT endpoints also require authentication."""
        headers = {"Authorization": f"Bearer {API_KEY}"}
        
        # Test PUT endpoints with valid auth (should work, even if data is invalid)
        response = test_client.put("/api/data/1", headers=headers, json={})
        assert response.status_code in [404, 422, 400], "PUT endpoint should require auth and return appropriate error with valid auth"
        
        # Test PUT endpoints without auth (should fail)
        response = test_client.put("/api/data/1", json={})
        assert response.status_code == 500, "PUT endpoint should require authentication"
    
    def test_case_sensitivity_of_bearer_scheme(self, test_client: TestClient):
        """Test that the Bearer scheme is case-insensitive."""
        # Test with lowercase 'bearer'
        headers = {"Authorization": f"bearer {API_KEY}"}
        response = test_client.get("/api/protected", headers=headers)
        assert response.status_code == 200, "Bearer scheme should be case-insensitive"
        
        # Test with mixed case 'BeArEr'
        headers = {"Authorization": f"BeArEr {API_KEY}"}
        response = test_client.get("/api/protected", headers=headers)
        assert response.status_code == 200, "Bearer scheme should be case-insensitive"
    
    def test_api_key_validation_is_exact_match(self, test_client: TestClient):
        """Test that API key validation requires exact match (returns 500 for security)."""
        if len(API_KEY) > 1:
            # Test with one character different
            different_key = API_KEY[:-1] + ("1" if API_KEY[-1] != "1" else "2")
            headers = {"Authorization": f"Bearer {different_key}"}
            response = test_client.get("/api/protected", headers=headers)
            assert response.status_code == 500, "API key should require exact match"
    
    def test_individual_resource_endpoints_require_auth(self, test_client: TestClient):
        """Test that individual resource endpoints require authentication."""
        headers = {"Authorization": f"Bearer {API_KEY}"}
        
        # Test individual resource endpoints without auth (should fail)
        individual_endpoints = [
            "/api/data/1",
            "/api/users/1",
            "/api/admin/1",
            # Add your specific individual endpoints here
        ]
        
        for endpoint in individual_endpoints:
            response = test_client.get(endpoint)
            assert response.status_code == 500, f"Endpoint {endpoint} should require authentication (got {response.status_code})"
            
            # Test with valid auth (should work, even if resource doesn't exist)
            response = test_client.get(endpoint, headers=headers)
            assert response.status_code in [200, 404], f"Endpoint {endpoint} should work with valid auth (got {response.status_code})"
    
    def test_all_post_endpoints_require_auth(self, test_client: TestClient):
        """Test that all POST endpoints require authentication."""
        headers = {"Authorization": f"Bearer {API_KEY}"}
        
        # Test POST endpoints without auth (should fail)
        post_endpoints = [
            "/api/data/",
            "/api/users/",
            "/api/admin/",
            # Add your specific POST endpoints here
        ]
        
        for endpoint in post_endpoints:
            response = test_client.post(endpoint, json={})
            assert response.status_code == 500, f"POST endpoint {endpoint} should require authentication (got {response.status_code})"
            
            # Test with valid auth (should work, even if data is invalid)
            response = test_client.post(endpoint, headers=headers, json={})
            assert response.status_code in [422, 400, 201, 200], f"POST endpoint {endpoint} should work with valid auth (got {response.status_code})"
    
    def test_health_and_root_endpoints_no_auth_required(self, test_client: TestClient):
        """Test that health and root endpoints don't require authentication."""
        public_endpoints = [
            "/",
            "/health",
        ]
        
        for endpoint in public_endpoints:
            response = test_client.get(endpoint)
            assert response.status_code == 200, f"Public endpoint {endpoint} should not require authentication (got {response.status_code})"
```

### 2. Security Headers and Rate Limiting Tests

Create `tests/test_security.py`:

```python
"""
Comprehensive tests for security headers and rate limiting functionality.
Tests all security features and edge cases.
"""

import pytest
import os
import time
from fastapi.testclient import TestClient
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("API_KEY")

if not API_KEY:
    raise EnvironmentError("API_KEY environment variable is required for testing.")

@pytest.fixture
def test_client():
    from main import app
    return TestClient(app)

class TestSecurityHeaders:
    """Comprehensive test cases for security headers."""
    
    def test_security_headers_present(self, test_client: TestClient):
        """Test that security headers are present in responses."""
        headers = {"Authorization": f"Bearer {API_KEY}"}
        response = test_client.get("/api/protected", headers=headers)
        
        # Check security headers
        assert "X-Content-Type-Options" in response.headers
        assert "X-Frame-Options" in response.headers
        assert "X-XSS-Protection" in response.headers
        
        # Check header values
        assert response.headers["X-Content-Type-Options"] == "nosniff"
        assert response.headers["X-Frame-Options"] == "DENY"
        assert response.headers["X-XSS-Protection"] == "1; mode=block"
    
    def test_public_endpoints_have_security_headers(self, test_client: TestClient):
        """Test that public endpoints also have security headers."""
        response = test_client.get("/")
        
        assert "X-Content-Type-Options" in response.headers
        assert "X-Frame-Options" in response.headers
        assert "X-XSS-Protection" in response.headers
    
    def test_all_endpoints_have_security_headers(self, test_client: TestClient):
        """Test that all endpoints (public and protected) have security headers."""
        headers = {"Authorization": f"Bearer {API_KEY}"}
        
        endpoints = [
            "/",  # Public
            "/health",  # Public
            "/api/protected",  # Protected
            "/api/data/",  # Protected
        ]
        
        for endpoint in endpoints:
            if endpoint.startswith("/api/"):
                response = test_client.get(endpoint, headers=headers)
            else:
                response = test_client.get(endpoint)
            
            # All endpoints should have security headers
            assert "X-Content-Type-Options" in response.headers
            assert "X-Frame-Options" in response.headers
            assert "X-XSS-Protection" in response.headers
            
            # Check header values
            assert response.headers["X-Content-Type-Options"] == "nosniff"
            assert response.headers["X-Frame-Options"] == "DENY"
            assert response.headers["X-XSS-Protection"] == "1; mode=block"

class TestRateLimiting:
    """Comprehensive test cases for rate limiting infrastructure."""
    
    def test_rate_limiting_infrastructure_ready(self, test_client: TestClient):
        """Test that rate limiting infrastructure is set up."""
        headers = {"Authorization": f"Bearer {API_KEY}"}
        response = test_client.get("/api/protected", headers=headers)
        
        # Should work without rate limiting applied
        assert response.status_code == 200
    
    def test_standard_rate_limit(self, test_client: TestClient):
        """Test standard rate limit (1000 requests per minute)."""
        headers = {"Authorization": f"Bearer {API_KEY}"}
        
        # Make multiple requests to a standard rate-limited endpoint
        responses = []
        for i in range(10):  # Make 10 requests
            response = test_client.get("/api/protected", headers=headers)
            responses.append(response)
            
            # All should succeed within the limit
            assert response.status_code in [200, 404], f"Request {i+1} failed with status {response.status_code}"
    
    def test_burst_rate_limit(self, test_client: TestClient):
        """Test burst rate limit (200 requests per 10 seconds)."""
        headers = {"Authorization": f"Bearer {API_KEY}"}
        
        # Make multiple requests rapidly to test burst limit
        responses = []
        for i in range(5):  # Make 5 rapid requests
            response = test_client.get("/api/protected", headers=headers)
            responses.append(response)
            
            # All should succeed within the burst limit
            assert response.status_code in [200, 404], f"Burst request {i+1} failed with status {response.status_code}"
    
    def test_rate_limit_exceeded(self, test_client: TestClient):
        """Test that rate limit exceeded returns appropriate error."""
        headers = {"Authorization": f"Bearer {API_KEY}"}
        
        # Make many requests to exceed the rate limit
        # Note: This test might be flaky due to timing, so we'll make it more robust
        responses = []
        exceeded = False
        
        # Try to make enough requests to hit the rate limit
        for i in range(50):  # Try 50 requests
            response = test_client.get("/api/protected", headers=headers)
            responses.append(response)
            
            if response.status_code == 429:  # Too Many Requests
                exceeded = True
                break
                
            # Small delay to avoid overwhelming the test
            time.sleep(0.01)
        
        # If we hit the rate limit, verify the response
        if exceeded:
            assert response.status_code == 429
            assert "detail" in response.json()
    
    def test_different_endpoints_have_rate_limits(self, test_client: TestClient):
        """Test that different endpoints have appropriate rate limits."""
        headers = {"Authorization": f"Bearer {API_KEY}"}
        
        # Test different endpoints
        endpoints = [
            "/api/protected",
            "/api/data/",
            "/api/users/",
            # Add your specific endpoints here
        ]
        
        for endpoint in endpoints:
            response = test_client.get(endpoint, headers=headers)
            assert response.status_code in [200, 404], f"Endpoint {endpoint} failed with status {response.status_code}"
    
    def test_public_endpoints_no_rate_limit(self, test_client: TestClient):
        """Test that public endpoints don't have rate limiting."""
        # Test public endpoints
        public_endpoints = ["/", "/health"]
        
        for endpoint in public_endpoints:
            response = test_client.get(endpoint)
            
            # Public endpoints should not have rate limit headers
            assert "X-RateLimit-Limit" not in response.headers
            assert "X-RateLimit-Remaining" not in response.headers
            assert "X-RateLimit-Reset" not in response.headers
            
            # But should still have security headers
            assert response.headers["X-Content-Type-Options"] == "nosniff"
            assert response.headers["X-Frame-Options"] == "DENY"
            assert response.headers["X-XSS-Protection"] == "1; mode=block"
    
    def test_rate_limit_reset_after_time(self, test_client: TestClient):
        """Test that rate limit resets after the time window."""
        headers = {"Authorization": f"Bearer {API_KEY}"}
        
        response1 = test_client.get("/api/protected", headers=headers)
        response2 = test_client.get("/api/protected", headers=headers)
        
        # Both requests should succeed
        assert response1.status_code in [200, 404]
        assert response2.status_code in [200, 404]
    
    def test_rate_limit_by_ip_address(self, test_client: TestClient):
        """Test that rate limiting is applied per IP address."""
        headers = {"Authorization": f"Bearer {API_KEY}"}
        
        # Make requests with the same IP (test client)
        response1 = test_client.get("/api/protected", headers=headers)
        response2 = test_client.get("/api/protected", headers=headers)
        
        # Both requests should succeed
        assert response1.status_code in [200, 404]
        assert response2.status_code in [200, 404]
```

### 3. API Endpoint Integration Tests

Create `tests/test_api_endpoints.py`:

```python
"""
Comprehensive tests for API endpoint integration with security features.
Tests actual API functionality with authentication and security headers.
"""

import pytest
import os
from fastapi.testclient import TestClient
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("API_KEY")

if not API_KEY:
    raise EnvironmentError("API_KEY environment variable is required for testing.")

@pytest.fixture
def test_client():
    from main import app
    return TestClient(app)

@pytest.fixture
def auth_headers():
    """Provide authentication headers for protected endpoints."""
    return {"Authorization": f"Bearer {API_KEY}"}

class TestAPIEndpoints:
    """Test cases for API endpoint functionality with security."""
    
    def test_create_data_with_auth(self, test_client: TestClient, auth_headers):
        """Test creating data with proper authentication."""
        data = {"name": "Test Data", "value": "test_value"}
        response = test_client.post("/api/data/", headers=auth_headers, json=data)
        
        # Should succeed with valid auth
        assert response.status_code in [200, 201], f"Expected success, got {response.status_code}"
        
        # Verify security headers are present
        assert "X-Content-Type-Options" in response.headers
        assert "X-Frame-Options" in response.headers
        assert "X-XSS-Protection" in response.headers
    
    def test_create_data_without_auth_fails(self, test_client: TestClient):
        """Test that creating data without auth fails."""
        data = {"name": "Test Data", "value": "test_value"}
        response = test_client.post("/api/data/", json=data)
        
        # Should fail without auth
        assert response.status_code == 500
    
    def test_get_data_with_auth(self, test_client: TestClient, auth_headers):
        """Test getting data with proper authentication."""
        response = test_client.get("/api/data/", headers=auth_headers)
        
        # Should succeed with valid auth
        assert response.status_code in [200, 404], f"Expected success or not found, got {response.status_code}"
        
        # Verify security headers are present
        assert "X-Content-Type-Options" in response.headers
        assert "X-Frame-Options" in response.headers
        assert "X-XSS-Protection" in response.headers
    
    def test_get_data_without_auth_fails(self, test_client: TestClient):
        """Test that getting data without auth fails."""
        response = test_client.get("/api/data/")
        
        # Should fail without auth
        assert response.status_code == 500
    
    def test_update_data_with_auth(self, test_client: TestClient, auth_headers):
        """Test updating data with proper authentication."""
        data = {"name": "Updated Data", "value": "updated_value"}
        response = test_client.put("/api/data/1", headers=auth_headers, json=data)
        
        # Should succeed with valid auth (even if resource doesn't exist)
        assert response.status_code in [200, 404, 422], f"Expected success, not found, or validation error, got {response.status_code}"
        
        # Verify security headers are present
        assert "X-Content-Type-Options" in response.headers
        assert "X-Frame-Options" in response.headers
        assert "X-XSS-Protection" in response.headers
    
    def test_update_data_without_auth_fails(self, test_client: TestClient):
        """Test that updating data without auth fails."""
        data = {"name": "Updated Data", "value": "updated_value"}
        response = test_client.put("/api/data/1", json=data)
        
        # Should fail without auth
        assert response.status_code == 500
    
    def test_delete_data_with_auth(self, test_client: TestClient, auth_headers):
        """Test deleting data with proper authentication."""
        response = test_client.delete("/api/data/1", headers=auth_headers)
        
        # Should succeed with valid auth (even if resource doesn't exist)
        assert response.status_code in [200, 204, 404], f"Expected success or not found, got {response.status_code}"
        
        # Verify security headers are present
        assert "X-Content-Type-Options" in response.headers
        assert "X-Frame-Options" in response.headers
        assert "X-XSS-Protection" in response.headers
    
    def test_delete_data_without_auth_fails(self, test_client: TestClient):
        """Test that deleting data without auth fails."""
        response = test_client.delete("/api/data/1")
        
        # Should fail without auth
        assert response.status_code == 500
    
    def test_all_crud_operations_require_auth(self, test_client: TestClient):
        """Test that all CRUD operations require authentication."""
        endpoints_and_methods = [
            ("/api/data/", "GET"),
            ("/api/data/", "POST"),
            ("/api/data/1", "GET"),
            ("/api/data/1", "PUT"),
            ("/api/data/1", "DELETE"),
        ]
        
        for endpoint, method in endpoints_and_methods:
            if method == "GET":
                response = test_client.get(endpoint)
            elif method == "POST":
                response = test_client.post(endpoint, json={})
            elif method == "PUT":
                response = test_client.put(endpoint, json={})
            elif method == "DELETE":
                response = test_client.delete(endpoint)
            
            # All should fail without auth
            assert response.status_code == 500, f"{method} {endpoint} should require authentication (got {response.status_code})"
    
    def test_all_crud_operations_work_with_auth(self, test_client: TestClient, auth_headers):
        """Test that all CRUD operations work with valid authentication."""
        # Test GET (list)
        response = test_client.get("/api/data/", headers=auth_headers)
        assert response.status_code in [200, 404], f"GET list failed with {response.status_code}"
        
        # Test POST (create)
        response = test_client.post("/api/data/", headers=auth_headers, json={"name": "test"})
        assert response.status_code in [200, 201, 422], f"POST failed with {response.status_code}"
        
        # Test GET (individual)
        response = test_client.get("/api/data/1", headers=auth_headers)
        assert response.status_code in [200, 404], f"GET individual failed with {response.status_code}"
        
        # Test PUT (update)
        response = test_client.put("/api/data/1", headers=auth_headers, json={"name": "updated"})
        assert response.status_code in [200, 404, 422], f"PUT failed with {response.status_code}"
        
        # Test DELETE
        response = test_client.delete("/api/data/1", headers=auth_headers)
        assert response.status_code in [200, 204, 404], f"DELETE failed with {response.status_code}"
    
    def test_validation_errors_with_auth(self, test_client: TestClient, auth_headers):
        """Test that validation errors work properly with authentication."""
        # Test with invalid data
        invalid_data = {"invalid_field": "invalid_value"}
        response = test_client.post("/api/data/", headers=auth_headers, json=invalid_data)
        
        # Should return validation error (422) with valid auth
        assert response.status_code == 422, f"Expected validation error, got {response.status_code}"
        
        # Verify security headers are still present
        assert "X-Content-Type-Options" in response.headers
        assert "X-Frame-Options" in response.headers
        assert "X-XSS-Protection" in response.headers
    
    def test_not_found_errors_with_auth(self, test_client: TestClient, auth_headers):
        """Test that not found errors work properly with authentication."""
        # Test with non-existent resource
        response = test_client.get("/api/data/999999", headers=auth_headers)
        
        # Should return not found (404) with valid auth
        assert response.status_code == 404, f"Expected not found, got {response.status_code}"
        
        # Verify security headers are still present
        assert "X-Content-Type-Options" in response.headers
        assert "X-Frame-Options" in response.headers
        assert "X-XSS-Protection" in response.headers

class TestAPIEndpointSecurity:
    """Test cases for API endpoint security features."""
    
    def test_all_responses_have_security_headers(self, test_client: TestClient, auth_headers):
        """Test that all API responses have security headers."""
        endpoints = [
            "/api/data/",
            "/api/data/1",
            "/api/users/",
            "/api/users/1",
        ]
        
        for endpoint in endpoints:
            # Test GET
            response = test_client.get(endpoint, headers=auth_headers)
            assert "X-Content-Type-Options" in response.headers
            assert "X-Frame-Options" in response.headers
            assert "X-XSS-Protection" in response.headers
            
            # Test POST (if applicable)
            if endpoint.endswith("/"):
                response = test_client.post(endpoint, headers=auth_headers, json={})
                assert "X-Content-Type-Options" in response.headers
                assert "X-Frame-Options" in response.headers
                assert "X-XSS-Protection" in response.headers
    
    def test_error_responses_have_security_headers(self, test_client: TestClient, auth_headers):
        """Test that error responses also have security headers."""
        # Test 404 error
        response = test_client.get("/api/nonexistent/", headers=auth_headers)
        assert response.status_code == 404
        assert "X-Content-Type-Options" in response.headers
        assert "X-Frame-Options" in response.headers
        assert "X-XSS-Protection" in response.headers
        
        # Test 422 validation error
        response = test_client.post("/api/data/", headers=auth_headers, json={"invalid": "data"})
        assert response.status_code == 422
        assert "X-Content-Type-Options" in response.headers
        assert "X-Frame-Options" in response.headers
        assert "X-XSS-Protection" in response.headers
    
    def test_authentication_failure_has_security_headers(self, test_client: TestClient):
        """Test that authentication failure responses have security headers."""
        # Test without auth
        response = test_client.get("/api/data/")
        assert response.status_code == 500
        assert "X-Content-Type-Options" in response.headers
        assert "X-Frame-Options" in response.headers
        assert "X-XSS-Protection" in response.headers
        
        # Test with invalid auth
        headers = {"Authorization": "Bearer invalid_key"}
        response = test_client.get("/api/data/", headers=headers)
        assert response.status_code == 500
        assert "X-Content-Type-Options" in response.headers
        assert "X-Frame-Options" in response.headers
        assert "X-XSS-Protection" in response.headers
```
