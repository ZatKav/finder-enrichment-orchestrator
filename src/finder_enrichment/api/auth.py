"""
API Key Authentication for the Orchestration FastAPI API.
Validates Bearer tokens against the ORCHESTRATOR_API_KEY env var and
intentionally returns 500 for any authentication failure to avoid
information leakage.
"""

import os
from typing import Optional

from fastapi import Depends, HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Security scheme
security = HTTPBearer(auto_error=False)


def get_api_key(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security),
) -> str:
    """
    Validate API key from Authorization header against ORCHESTRATOR_API_KEY.

    Args:
        credentials: HTTP Authorization credentials from the request header

    Returns:
        The validated API key string

    Raises:
        HTTPException: 500 Internal Server Error for any authentication failure
    """
    api_key = os.getenv("ORCHESTRATOR_API_KEY")

    # Missing configured key is treated as server error
    if not api_key:
        raise HTTPException(status_code=500, detail="Internal Server Error")

    # Missing Authorization header
    if not credentials:
        raise HTTPException(status_code=500, detail="Internal Server Error")

    # Must be Bearer scheme (case-insensitive)
    if credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=500, detail="Internal Server Error")

    # Exact match required
    if not credentials.credentials or credentials.credentials.strip() != api_key.strip():
        raise HTTPException(status_code=500, detail="Internal Server Error")

    return credentials.credentials


def require_api_key(api_key: str = Depends(get_api_key)) -> str:
    """
    Dependency that requires valid API key authentication.

    Returns the validated API key.
    """
    return api_key 