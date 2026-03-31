"""Comprehensive integration tests for security features."""

import pytest

from security.auth import create_access_token, User
from security.rbac import Role, Permission, check_permission
from security.encryption import encrypt_data, decrypt_data, encrypt_pii_fields
from security.pii_redaction import redact_pii, redact_transcription
from security.identity_verification import (
    generate_verification_code,
    store_verification_code,
    verify_code,
)


def test_end_to_end_authentication_flow():
    """Test complete authentication flow."""
    # 1. Create user token
    user_data = {
        "user_id": "user-123",
        "email": "test@example.com",
        "role": "technician"
    }
    token = create_access_token(user_data)
    
    # 2. Verify token is created
    assert token is not None
    assert isinstance(token, str)
    assert len(token) > 0


def test_end_to_end_data_encryption_flow():
    """Test complete data encryption and storage flow."""
    # 1. Simulate user data with PII
    user_data = {
        "name": "John Doe",
        "email": "john@example.com",
        "ssn": "123-45-6789",
        "phone": "555-1234",
        "job_title": "Technician"
    }
    
    # 2. Encrypt PII fields before storage
    pii_fields = ["email", "ssn", "phone"]
    encrypted_data = encrypt_pii_fields(user_data, pii_fields)
    
    # 3. Verify PII is encrypted
    assert encrypted_data["email"] != user_data["email"]
    assert encrypted_data["ssn"] != user_data["ssn"]
    assert encrypted_data["phone"] != user_data["phone"]
    assert encrypted_data["name"] == user_data["name"]  # Not encrypted
    
    # 4. Decrypt for authorized access
    decrypted_email = decrypt_data(encrypted_data["email"])
    assert decrypted_email == user_data["email"]


def test_end_to_end_pii_redaction_flow():
    """Test complete PII redaction flow for transcriptions."""
    # 1. Simulate voice transcription with PII
    transcription = """
    Customer: Hi, my name is John Doe and I need help with my furnace.
    My email is john.doe@example.com and my phone is 555-123-4567.
    My SSN is 123-45-6789 for verification.
    """
    
    # 2. Redact PII from transcription
    result = redact_transcription(transcription)
    
    # 3. Verify PII is redacted
    assert "john.doe@example.com" not in result["redacted_text"]
    assert "555-123-4567" not in result["redacted_text"]
    assert "123-45-6789" not in result["redacted_text"]
    assert "[EMAIL-REDACTED]" in result["redacted_text"]
    assert result["pii_count"] > 0
    
    # 4. Verify structure is preserved
    assert "Customer:" in result["redacted_text"]
    assert "furnace" in result["redacted_text"]


def test_end_to_end_identity_verification_flow():
    """Test complete identity verification flow."""
    email = "newuser@example.com"
    
    # 1. Generate verification code
    code = generate_verification_code()
    assert len(code) == 6
    
    # 2. Store code
    store_verification_code(email, code)
    
    # 3. Verify with correct code
    is_valid = verify_code(email, code)
    assert is_valid is True
    
    # 4. Try to verify again (should fail - code removed)
    is_valid = verify_code(email, code)
    assert is_valid is False


def test_rbac_role_hierarchy():
    """Test RBAC role hierarchy and permissions."""
    # Customer has minimal permissions
    customer = User(id="c1", email="customer@example.com", role="customer")
    assert check_permission(customer, Permission.READ_JOBS) is True
    assert check_permission(customer, Permission.WRITE_JOBS) is False
    
    # Technician has more permissions
    technician = User(id="t1", email="tech@example.com", role="technician")
    assert check_permission(technician, Permission.READ_JOBS) is True
    assert check_permission(technician, Permission.WRITE_JOBS) is True
    assert check_permission(technician, Permission.MANAGE_USERS) is False
    
    # Dispatcher has scheduling permissions
    dispatcher = User(id="d1", email="dispatcher@example.com", role="dispatcher")
    assert check_permission(dispatcher, Permission.MANAGE_SCHEDULE) is True
    assert check_permission(dispatcher, Permission.ACCESS_REPORTS) is True
    
    # Admin has all permissions
    admin = User(id="a1", email="admin@example.com", role="admin")
    assert check_permission(admin, Permission.READ_JOBS) is True
    assert check_permission(admin, Permission.WRITE_JOBS) is True
    assert check_permission(admin, Permission.MANAGE_USERS) is True
    assert check_permission(admin, Permission.MANAGE_SYSTEM) is True


def test_encryption_with_multiple_fields():
    """Test encryption of multiple PII fields."""
    data = {
        "customer_name": "Jane Smith",
        "email": "jane@example.com",
        "phone": "555-9876",
        "ssn": "987-65-4321",
        "address": "123 Main St",
        "job_type": "HVAC Repair"
    }
    
    pii_fields = ["email", "phone", "ssn", "address"]
    encrypted = encrypt_pii_fields(data, pii_fields)
    
    # All PII fields should be encrypted
    for field in pii_fields:
        assert encrypted[field] != data[field]
    
    # Non-PII fields should remain unchanged
    assert encrypted["customer_name"] == data["customer_name"]
    assert encrypted["job_type"] == data["job_type"]


def test_pii_redaction_multiple_types():
    """Test redaction of multiple PII types in single text."""
    text = """
    Customer Information:
    Name: John Doe
    Email: john@example.com
    Phone: (555) 123-4567
    SSN: 123-45-6789
    Card: 4532-1234-5678-9010
    Address: 456 Oak Street
    """
    
    redacted, matches = redact_pii(text)
    
    # Check that various PII types are detected
    pii_types = {m.type for m in matches}
    assert "email" in pii_types
    assert "phone" in pii_types
    assert "ssn" in pii_types
    
    # Check that PII is redacted
    assert "john@example.com" not in redacted
    assert "123-45-6789" not in redacted


def test_token_expiration_enforcement():
    """Test that expired tokens are rejected."""
    from datetime import timedelta
    from security.auth import verify_access_token
    from fastapi import HTTPException
    
    # Create token with very short expiration
    token = create_access_token(
        {"user_id": "test", "email": "test@example.com", "role": "technician"},
        expires_delta=timedelta(seconds=-1)  # Already expired
    )
    
    # Try to verify expired token
    with pytest.raises(HTTPException) as exc_info:
        verify_access_token(token)
    
    assert exc_info.value.status_code == 401


def test_verification_code_max_attempts():
    """Test verification code max attempts limit."""
    email = "test@example.com"
    code = "123456"
    
    store_verification_code(email, code)
    
    # Try wrong code 3 times
    for _ in range(3):
        result = verify_code(email, "wrong")
        assert result is False
    
    # Now try correct code - should fail (max attempts exceeded)
    result = verify_code(email, code)
    assert result is False


def test_aes_256_encryption_strength():
    """Test that AES-256 encryption is properly implemented."""
    plaintext = "Sensitive data"
    
    # Encrypt multiple times
    encrypted1 = encrypt_data(plaintext)
    encrypted2 = encrypt_data(plaintext)
    
    # Different IVs should produce different ciphertexts
    assert encrypted1 != encrypted2
    
    # Both should decrypt correctly
    assert decrypt_data(encrypted1) == plaintext
    assert decrypt_data(encrypted2) == plaintext


def test_role_based_job_access():
    """Test role-based access to job operations."""
    # Customer can read but not write
    customer = User(id="c1", email="customer@example.com", role="customer")
    assert check_permission(customer, Permission.READ_JOBS) is True
    assert check_permission(customer, Permission.WRITE_JOBS) is False
    
    # Technician can read and write
    technician = User(id="t1", email="tech@example.com", role="technician")
    assert check_permission(technician, Permission.READ_JOBS) is True
    assert check_permission(technician, Permission.WRITE_JOBS) is True
    
    # Dispatcher can read, write, and manage schedule
    dispatcher = User(id="d1", email="dispatcher@example.com", role="dispatcher")
    assert check_permission(dispatcher, Permission.READ_JOBS) is True
    assert check_permission(dispatcher, Permission.WRITE_JOBS) is True
    assert check_permission(dispatcher, Permission.MANAGE_SCHEDULE) is True


def test_rbac_authorization_flow():
    """Test RBAC authorization flow."""
    # Create technician user (no admin permissions)
    tech_user = User(id="tech-1", email="tech@example.com", role="technician")
    
    # Technician cannot manage users
    assert check_permission(tech_user, Permission.MANAGE_USERS) is False
    
    # Create admin user
    admin_user = User(id="admin-1", email="admin@example.com", role="admin")
    
    # Admin can manage users
    assert check_permission(admin_user, Permission.MANAGE_USERS) is True
