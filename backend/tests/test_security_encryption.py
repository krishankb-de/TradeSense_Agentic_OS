"""Unit tests for encryption module."""

import pytest
import os

from security.encryption import (
    encrypt_data,
    decrypt_data,
    encrypt_pii_fields,
    decrypt_pii_fields,
)


def test_encrypt_decrypt_string():
    """Test encryption and decryption of string data."""
    plaintext = "This is sensitive data"
    
    encrypted = encrypt_data(plaintext)
    assert encrypted != plaintext
    assert isinstance(encrypted, str)
    
    decrypted = decrypt_data(encrypted)
    assert decrypted == plaintext


def test_encrypt_decrypt_bytes():
    """Test encryption and decryption of bytes data."""
    plaintext = b"Binary sensitive data"
    
    encrypted = encrypt_data(plaintext)
    assert encrypted != plaintext.decode('utf-8')
    
    decrypted = decrypt_data(encrypted)
    assert decrypted == plaintext.decode('utf-8')


def test_encrypt_produces_different_ciphertext():
    """Test that encrypting same plaintext produces different ciphertext (due to random IV)."""
    plaintext = "Same data"
    
    encrypted1 = encrypt_data(plaintext)
    encrypted2 = encrypt_data(plaintext)
    
    # Different IVs should produce different ciphertexts
    assert encrypted1 != encrypted2
    
    # But both should decrypt to same plaintext
    assert decrypt_data(encrypted1) == plaintext
    assert decrypt_data(encrypted2) == plaintext


def test_decrypt_invalid_data():
    """Test decryption of invalid data raises error."""
    invalid_encrypted = "invalid_base64_data"
    
    with pytest.raises(Exception):
        decrypt_data(invalid_encrypted)


def test_encrypt_empty_string():
    """Test encryption of empty string."""
    plaintext = ""
    
    encrypted = encrypt_data(plaintext)
    decrypted = decrypt_data(encrypted)
    
    assert decrypted == plaintext


def test_encrypt_long_text():
    """Test encryption of long text."""
    plaintext = "A" * 10000  # 10KB of data
    
    encrypted = encrypt_data(plaintext)
    decrypted = decrypt_data(encrypted)
    
    assert decrypted == plaintext


def test_encrypt_pii_fields():
    """Test encryption of specific PII fields in dictionary."""
    data = {
        "name": "John Doe",
        "email": "john@example.com",
        "ssn": "123-45-6789",
        "public_field": "Not sensitive"
    }
    
    fields_to_encrypt = ["email", "ssn"]
    encrypted_data = encrypt_pii_fields(data, fields_to_encrypt)
    
    # Encrypted fields should be different
    assert encrypted_data["email"] != data["email"]
    assert encrypted_data["ssn"] != data["ssn"]
    
    # Non-encrypted fields should be same
    assert encrypted_data["name"] == data["name"]
    assert encrypted_data["public_field"] == data["public_field"]


def test_decrypt_pii_fields():
    """Test decryption of specific PII fields in dictionary."""
    data = {
        "name": "Jane Smith",
        "email": "jane@example.com",
        "phone": "555-1234"
    }
    
    fields = ["email", "phone"]
    
    # Encrypt
    encrypted_data = encrypt_pii_fields(data, fields)
    
    # Decrypt
    decrypted_data = decrypt_pii_fields(encrypted_data, fields)
    
    assert decrypted_data["email"] == data["email"]
    assert decrypted_data["phone"] == data["phone"]
    assert decrypted_data["name"] == data["name"]


def test_encrypt_pii_fields_missing_field():
    """Test encryption handles missing fields gracefully."""
    data = {
        "name": "Test User",
        "email": "test@example.com"
    }
    
    fields_to_encrypt = ["email", "ssn", "phone"]  # ssn and phone don't exist
    encrypted_data = encrypt_pii_fields(data, fields_to_encrypt)
    
    assert encrypted_data["email"] != data["email"]
    assert "ssn" not in encrypted_data
    assert "phone" not in encrypted_data


def test_decrypt_pii_fields_non_encrypted():
    """Test decryption handles non-encrypted fields gracefully."""
    data = {
        "name": "Test User",
        "email": "plain@example.com"  # Not encrypted
    }
    
    # Try to decrypt non-encrypted field
    decrypted_data = decrypt_pii_fields(data, ["email"])
    
    # Should leave as is if decryption fails
    assert "email" in decrypted_data


def test_aes_256_encryption():
    """Test that AES-256 encryption is used (32-byte key)."""
    from security.encryption import ENCRYPTION_KEY
    
    # AES-256 requires 32-byte key
    assert len(ENCRYPTION_KEY) == 32


def test_encrypt_unicode_characters():
    """Test encryption of unicode characters."""
    plaintext = "Hello 世界 🌍"
    
    encrypted = encrypt_data(plaintext)
    decrypted = decrypt_data(encrypted)
    
    assert decrypted == plaintext
