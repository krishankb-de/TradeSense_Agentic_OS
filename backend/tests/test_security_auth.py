"""Unit tests for authentication module."""

import pytest
from datetime import timedelta
import jwt

from security.auth import (
    create_access_token,
    verify_access_token,
    SECRET_KEY,
    ALGORITHM,
)


def test_create_access_token():
    """Test JWT token creation."""
    data = {
        "user_id": "test-user-123",
        "email": "test@example.com",
        "role": "technician"
    }
    
    token = create_access_token(data)
    
    assert token is not None
    assert isinstance(token, str)
    
    # Decode and verify
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    assert payload["user_id"] == data["user_id"]
    assert payload["email"] == data["email"]
    assert payload["role"] == data["role"]
    assert "exp" in payload


def test_create_access_token_custom_expiry():
    """Test JWT token creation with custom expiration."""
    data = {
        "user_id": "test-user-123",
        "email": "test@example.com",
        "role": "admin"
    }
    
    expires_delta = timedelta(minutes=30)
    token = create_access_token(data, expires_delta)
    
    assert token is not None
    
    # Decode and verify expiration
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    assert "exp" in payload


def test_verify_access_token_valid():
    """Test verification of valid JWT token."""
    data = {
        "user_id": "test-user-456",
        "email": "user@example.com",
        "role": "dispatcher"
    }
    
    token = create_access_token(data)
    token_data = verify_access_token(token)
    
    assert token_data.user_id == data["user_id"]
    assert token_data.email == data["email"]
    assert token_data.role == data["role"]


def test_verify_access_token_invalid():
    """Test verification of invalid JWT token."""
    from fastapi import HTTPException
    
    invalid_token = "invalid.token.here"
    
    with pytest.raises(HTTPException) as exc_info:
        verify_access_token(invalid_token)
    
    assert exc_info.value.status_code == 401


def test_verify_access_token_expired():
    """Test verification of expired JWT token."""
    from fastapi import HTTPException
    
    data = {
        "user_id": "test-user-789",
        "email": "expired@example.com",
        "role": "customer"
    }
    
    # Create token with negative expiration (already expired)
    expires_delta = timedelta(seconds=-1)
    token = create_access_token(data, expires_delta)
    
    with pytest.raises(HTTPException) as exc_info:
        verify_access_token(token)
    
    assert exc_info.value.status_code == 401
    assert "expired" in exc_info.value.detail.lower()


def test_token_expiration_one_hour():
    """Test that default token expiration is 1 hour."""
    from security.auth import ACCESS_TOKEN_EXPIRE_MINUTES
    
    assert ACCESS_TOKEN_EXPIRE_MINUTES == 60


def test_verify_access_token_missing_fields():
    """Test verification fails with missing required fields."""
    from fastapi import HTTPException
    
    # Create token with missing fields
    incomplete_data = {"user_id": "test-user"}
    token = jwt.encode(incomplete_data, SECRET_KEY, algorithm=ALGORITHM)
    
    with pytest.raises(HTTPException) as exc_info:
        verify_access_token(token)
    
    assert exc_info.value.status_code == 401
