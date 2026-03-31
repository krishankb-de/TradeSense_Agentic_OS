"""Unit tests for PII redaction module."""

import pytest

from security.pii_redaction import (
    detect_pii,
    redact_pii,
    anonymize_data,
    redact_transcription,
    is_sensitive_data,
    get_pii_summary,
)


def test_detect_ssn():
    """Test detection of Social Security Numbers."""
    text = "My SSN is 123-45-6789 and my friend's is 987654321"
    
    matches = detect_pii(text)
    
    ssn_matches = [m for m in matches if m.type == "ssn"]
    assert len(ssn_matches) == 2


def test_detect_credit_card():
    """Test detection of credit card numbers."""
    text = "My card number is 4532-1234-5678-9010"
    
    matches = detect_pii(text)
    
    cc_matches = [m for m in matches if m.type == "credit_card"]
    assert len(cc_matches) == 1


def test_detect_email():
    """Test detection of email addresses."""
    text = "Contact me at john.doe@example.com or jane@test.org"
    
    matches = detect_pii(text)
    
    email_matches = [m for m in matches if m.type == "email"]
    assert len(email_matches) == 2


def test_detect_phone():
    """Test detection of phone numbers."""
    text = "Call me at (555) 123-4567 or 555-987-6543"
    
    matches = detect_pii(text)
    
    phone_matches = [m for m in matches if m.type == "phone"]
    assert len(phone_matches) >= 1


def test_detect_address():
    """Test detection of street addresses."""
    text = "I live at 123 Main Street"
    
    matches = detect_pii(text)
    
    address_matches = [m for m in matches if m.type == "address"]
    assert len(address_matches) >= 1


def test_redact_ssn():
    """Test redaction of SSN."""
    text = "My SSN is 123-45-6789"
    
    redacted, matches = redact_pii(text, ["ssn"])
    
    assert "123-45-6789" not in redacted
    assert "[SSN-REDACTED]" in redacted
    assert len(matches) == 1


def test_redact_credit_card():
    """Test redaction of credit card numbers."""
    text = "Card: 4532-1234-5678-9010"
    
    redacted, matches = redact_pii(text, ["credit_card"])
    
    assert "4532-1234-5678-9010" not in redacted
    assert "[CARD-REDACTED]" in redacted


def test_redact_email():
    """Test redaction of email addresses."""
    text = "Email me at test@example.com"
    
    redacted, matches = redact_pii(text, ["email"])
    
    assert "test@example.com" not in redacted
    assert "[EMAIL-REDACTED]" in redacted


def test_redact_multiple_pii_types():
    """Test redaction of multiple PII types."""
    text = "My email is john@example.com and SSN is 123-45-6789"
    
    redacted, matches = redact_pii(text)
    
    assert "john@example.com" not in redacted
    assert "123-45-6789" not in redacted
    assert "[EMAIL-REDACTED]" in redacted
    assert "[SSN-REDACTED]" in redacted
    assert len(matches) == 2


def test_redact_no_pii():
    """Test redaction of text with no PII."""
    text = "This is a normal sentence with no sensitive data"
    
    redacted, matches = redact_pii(text)
    
    assert redacted == text
    assert len(matches) == 0


def test_anonymize_data():
    """Test anonymization of dictionary data."""
    data = {
        "name": "John Doe",
        "email": "john@example.com",
        "phone": "555-1234",
        "job_id": "job-123"
    }
    
    anonymized = anonymize_data(data, ["name", "email", "phone"])
    
    assert anonymized["name"] != data["name"]
    assert anonymized["email"] != data["email"]
    assert anonymized["phone"] != data["phone"]
    assert anonymized["job_id"] == data["job_id"]  # Not in anonymize list


def test_redact_transcription():
    """Test redaction of voice transcription."""
    transcription = "My name is John and my SSN is 123-45-6789"
    
    result = redact_transcription(transcription)
    
    assert "redacted_text" in result
    assert "detected_pii" in result
    assert "pii_count" in result
    assert result["pii_count"] > 0
    assert "123-45-6789" not in result["redacted_text"]


def test_is_sensitive_data_true():
    """Test detection of sensitive data."""
    text = "My SSN is 123-45-6789"
    
    assert is_sensitive_data(text) is True


def test_is_sensitive_data_false():
    """Test detection of non-sensitive data."""
    text = "This is just normal text"
    
    assert is_sensitive_data(text) is False


def test_is_sensitive_data_threshold():
    """Test sensitive data detection with custom threshold."""
    text = "My email is test@example.com"
    
    assert is_sensitive_data(text, threshold=1) is True
    assert is_sensitive_data(text, threshold=2) is False


def test_get_pii_summary():
    """Test PII summary generation."""
    text = "Email: test@example.com, SSN: 123-45-6789, Phone: 555-1234"
    
    summary = get_pii_summary(text)
    
    assert "email" in summary
    assert "ssn" in summary
    assert "phone" in summary
    assert summary["email"] >= 1
    assert summary["ssn"] >= 1


def test_redact_preserves_text_structure():
    """Test that redaction preserves overall text structure."""
    text = "Hello, my email is john@example.com and I need help."
    
    redacted, _ = redact_pii(text)
    
    assert redacted.startswith("Hello")
    assert redacted.endswith("help.")
    assert "email" in redacted


def test_detect_pii_confidence():
    """Test that detected PII has confidence scores."""
    text = "SSN: 123-45-6789"
    
    matches = detect_pii(text)
    
    assert len(matches) > 0
    assert all(m.confidence > 0 for m in matches)


def test_redact_zip_code():
    """Test redaction of ZIP codes."""
    text = "My ZIP is 12345"
    
    redacted, matches = redact_pii(text, ["zip_code"])
    
    assert "12345" not in redacted
    assert "[ZIP-REDACTED]" in redacted


def test_redact_date_of_birth():
    """Test redaction of dates of birth."""
    text = "Born on 01/15/1990"
    
    redacted, matches = redact_pii(text, ["date_of_birth"])
    
    assert "01/15/1990" not in redacted
    assert "[DOB-REDACTED]" in redacted
