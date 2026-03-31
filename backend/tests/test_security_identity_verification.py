"""Unit tests for identity verification module."""

import pytest
from datetime import datetime, timedelta

from security.identity_verification import (
    generate_verification_code,
    store_verification_code,
    verify_code,
    cleanup_expired_codes,
    _verification_codes,
)


def setup_function():
    """Clear verification codes before each test."""
    _verification_codes.clear()


def test_generate_verification_code_default_length():
    """Test generation of 6-digit verification code."""
    code = generate_verification_code()
    
    assert len(code) == 6
    assert code.isdigit()


def test_generate_verification_code_custom_length():
    """Test generation of custom length verification code."""
    code = generate_verification_code(length=8)
    
    assert len(code) == 8
    assert code.isdigit()


def test_generate_verification_code_uniqueness():
    """Test that generated codes are different."""
    codes = [generate_verification_code() for _ in range(10)]
    
    # Most codes should be unique (very unlikely to get duplicates)
    assert len(set(codes)) > 5


def test_store_verification_code():
    """Test storing verification code."""
    identifier = "test@example.com"
    code = "123456"
    
    store_verification_code(identifier, code)
    
    assert identifier in _verification_codes
    assert "code_hash" in _verification_codes[identifier]
    assert "expires_at" in _verification_codes[identifier]


def test_verify_code_valid():
    """Test verification of valid code."""
    identifier = "test@example.com"
    code = "123456"
    
    store_verification_code(identifier, code)
    result = verify_code(identifier, code)
    
    assert result is True
    # Code should be removed after successful verification
    assert identifier not in _verification_codes


def test_verify_code_invalid():
    """Test verification of invalid code."""
    identifier = "test@example.com"
    correct_code = "123456"
    wrong_code = "654321"
    
    store_verification_code(identifier, correct_code)
    result = verify_code(identifier, wrong_code)
    
    assert result is False


def test_verify_code_nonexistent():
    """Test verification of code for nonexistent identifier."""
    result = verify_code("nonexistent@example.com", "123456")
    
    assert result is False


def test_verify_code_expired():
    """Test verification of expired code."""
    identifier = "test@example.com"
    code = "123456"
    
    # Store with negative expiry (already expired)
    store_verification_code(identifier, code, expiry_minutes=-1)
    result = verify_code(identifier, code)
    
    assert result is False
    assert identifier not in _verification_codes


def test_verify_code_max_attempts():
    """Test max attempts limit for verification."""
    identifier = "test@example.com"
    code = "123456"
    
    store_verification_code(identifier, code)
    
    # Try wrong code 3 times
    for _ in range(3):
        verify_code(identifier, "wrong")
    
    # Code should be removed after max attempts
    assert identifier not in _verification_codes


def test_verify_code_attempts_increment():
    """Test that attempts are incremented."""
    identifier = "test@example.com"
    code = "123456"
    
    store_verification_code(identifier, code)
    
    # First wrong attempt
    verify_code(identifier, "wrong")
    assert _verification_codes[identifier]["attempts"] == 1
    
    # Second wrong attempt
    verify_code(identifier, "wrong")
    assert _verification_codes[identifier]["attempts"] == 2


def test_cleanup_expired_codes():
    """Test cleanup of expired verification codes."""
    # Store some codes
    store_verification_code("user1@example.com", "111111", expiry_minutes=10)
    store_verification_code("user2@example.com", "222222", expiry_minutes=-1)  # Expired
    store_verification_code("user3@example.com", "333333", expiry_minutes=-1)  # Expired
    
    removed = cleanup_expired_codes()
    
    assert removed == 2
    assert "user1@example.com" in _verification_codes
    assert "user2@example.com" not in _verification_codes
    assert "user3@example.com" not in _verification_codes


def test_code_hashing():
    """Test that codes are stored as hashes, not plaintext."""
    identifier = "test@example.com"
    code = "123456"
    
    store_verification_code(identifier, code)
    
    # Code should be hashed
    stored_hash = _verification_codes[identifier]["code_hash"]
    assert stored_hash != code
    assert len(stored_hash) == 64  # SHA-256 produces 64-character hex string


def test_verification_code_expiry_time():
    """Test that verification codes have correct expiry time."""
    from datetime import timezone
    
    identifier = "test@example.com"
    code = "123456"
    expiry_minutes = 10
    
    before = datetime.now(timezone.utc) + timedelta(minutes=expiry_minutes)
    store_verification_code(identifier, code, expiry_minutes=expiry_minutes)
    after = datetime.now(timezone.utc) + timedelta(minutes=expiry_minutes)
    
    expires_at = _verification_codes[identifier]["expires_at"]
    
    assert before <= expires_at <= after


def test_multiple_identifiers():
    """Test storing codes for multiple identifiers."""
    store_verification_code("user1@example.com", "111111")
    store_verification_code("user2@example.com", "222222")
    store_verification_code("+1234567890", "333333")
    
    assert len(_verification_codes) == 3
    assert verify_code("user1@example.com", "111111") is True
    assert verify_code("user2@example.com", "222222") is True
    assert verify_code("+1234567890", "333333") is True
