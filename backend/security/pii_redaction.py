"""PII detection and redaction for transcriptions and data."""

import re
from typing import List, Dict, Tuple
from dataclasses import dataclass


@dataclass
class PIIMatch:
    """Represents a detected PII match."""
    type: str
    value: str
    start: int
    end: int
    confidence: float


# PII detection patterns
PII_PATTERNS = {
    "ssn": {
        "pattern": r'\b\d{3}-\d{2}-\d{4}\b|\b\d{9}\b',
        "description": "Social Security Number",
        "replacement": "[SSN-REDACTED]"
    },
    "credit_card": {
        "pattern": r'\b(?:\d{4}[-\s]?){3}\d{4}\b',
        "description": "Credit Card Number",
        "replacement": "[CARD-REDACTED]"
    },
    "email": {
        "pattern": r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
        "description": "Email Address",
        "replacement": "[EMAIL-REDACTED]"
    },
    "phone": {
        "pattern": r'\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b|\b\d{3}-\d{4}\b',
        "description": "Phone Number",
        "replacement": "[PHONE-REDACTED]"
    },
    "address": {
        "pattern": r'\b\d{1,5}\s+[\w\s]{1,50}(?:street|st|avenue|ave|road|rd|highway|hwy|square|sq|trail|trl|drive|dr|court|ct|parkway|pkwy|circle|cir|boulevard|blvd)\b',
        "description": "Street Address",
        "replacement": "[ADDRESS-REDACTED]"
    },
    "zip_code": {
        "pattern": r'\b\d{5}(?:-\d{4})?\b',
        "description": "ZIP Code",
        "replacement": "[ZIP-REDACTED]"
    },
    "date_of_birth": {
        "pattern": r'\b(?:0?[1-9]|1[0-2])[/-](?:0?[1-9]|[12]\d|3[01])[/-](?:19|20)\d{2}\b',
        "description": "Date of Birth",
        "replacement": "[DOB-REDACTED]"
    },
}


def detect_pii(text: str) -> List[PIIMatch]:
    """
    Detect PII in text using pattern matching.
    
    Args:
        text: Text to scan for PII
        
    Returns:
        List of PIIMatch objects for detected PII
    """
    matches = []
    
    for pii_type, config in PII_PATTERNS.items():
        pattern = re.compile(config["pattern"], re.IGNORECASE)
        
        for match in pattern.finditer(text):
            matches.append(PIIMatch(
                type=pii_type,
                value=match.group(),
                start=match.start(),
                end=match.end(),
                confidence=0.9  # Pattern-based detection has high confidence
            ))
    
    # Sort by start position
    matches.sort(key=lambda x: x.start)
    
    return matches


def redact_pii(text: str, pii_types: List[str] = None) -> Tuple[str, List[PIIMatch]]:
    """
    Redact PII from text.
    
    Args:
        text: Text to redact
        pii_types: Optional list of specific PII types to redact (default: all)
        
    Returns:
        Tuple of (redacted_text, list of detected PII matches)
    """
    if pii_types is None:
        pii_types = list(PII_PATTERNS.keys())
    
    detected_pii = []
    redacted_text = text
    offset = 0  # Track offset due to replacements
    
    for pii_type in pii_types:
        if pii_type not in PII_PATTERNS:
            continue
        
        config = PII_PATTERNS[pii_type]
        pattern = re.compile(config["pattern"], re.IGNORECASE)
        
        for match in pattern.finditer(text):
            detected_pii.append(PIIMatch(
                type=pii_type,
                value=match.group(),
                start=match.start(),
                end=match.end(),
                confidence=0.9
            ))
            
            # Replace in redacted text (accounting for offset)
            start_pos = match.start() + offset
            end_pos = match.end() + offset
            replacement = config["replacement"]
            
            redacted_text = (
                redacted_text[:start_pos] +
                replacement +
                redacted_text[end_pos:]
            )
            
            # Update offset
            offset += len(replacement) - (match.end() - match.start())
    
    return redacted_text, detected_pii


def anonymize_data(data: dict, fields_to_anonymize: List[str] = None) -> dict:
    """
    Anonymize PII in dictionary data for analytics.
    
    Args:
        data: Dictionary containing data
        fields_to_anonymize: Optional list of fields to anonymize (default: common PII fields)
        
    Returns:
        Dictionary with PII anonymized
    """
    if fields_to_anonymize is None:
        fields_to_anonymize = [
            "name", "email", "phone", "address", "ssn",
            "credit_card", "date_of_birth", "customer_name"
        ]
    
    anonymized = data.copy()
    
    for field in fields_to_anonymize:
        if field in anonymized and anonymized[field]:
            if isinstance(anonymized[field], str):
                # Redact PII in string fields
                redacted_text, _ = redact_pii(anonymized[field])
                # If no PII detected, use generic placeholder
                if redacted_text == anonymized[field]:
                    anonymized[field] = f"[{field.upper()}-ANONYMIZED]"
                else:
                    anonymized[field] = redacted_text
            elif anonymized[field] is not None:
                # Replace non-string PII with generic placeholder
                anonymized[field] = f"[{field.upper()}-ANONYMIZED]"
    
    return anonymized


def redact_transcription(transcription: str) -> Dict[str, any]:
    """
    Redact PII from voice transcription.
    
    Args:
        transcription: Voice transcription text
        
    Returns:
        Dictionary with redacted_text and detected_pii list
    """
    redacted_text, detected_pii = redact_pii(transcription)
    
    return {
        "original_length": len(transcription),
        "redacted_text": redacted_text,
        "detected_pii": [
            {
                "type": match.type,
                "position": f"{match.start}-{match.end}",
                "confidence": match.confidence
            }
            for match in detected_pii
        ],
        "pii_count": len(detected_pii)
    }


def is_sensitive_data(text: str, threshold: int = 1) -> bool:
    """
    Check if text contains sensitive PII.
    
    Args:
        text: Text to check
        threshold: Minimum number of PII matches to consider sensitive
        
    Returns:
        True if text contains PII above threshold
    """
    detected = detect_pii(text)
    return len(detected) >= threshold


def get_pii_summary(text: str) -> Dict[str, int]:
    """
    Get summary of PII types detected in text.
    
    Args:
        text: Text to analyze
        
    Returns:
        Dictionary mapping PII types to count
    """
    detected = detect_pii(text)
    summary = {}
    
    for match in detected:
        summary[match.type] = summary.get(match.type, 0) + 1
    
    return summary
