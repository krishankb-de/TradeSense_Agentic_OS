"""Security module for TradeSense authentication, authorization, and data protection."""

from .auth import (
    create_access_token,
    verify_access_token,
    get_current_user,
    oauth2_scheme,
)
from .rbac import (
    Role,
    Permission,
    check_permission,
    require_permission,
)
from .encryption import (
    encrypt_data,
    decrypt_data,
    encrypt_file,
    decrypt_file,
)
from .pii_redaction import (
    detect_pii,
    redact_pii,
    anonymize_data,
)
from .identity_verification import (
    generate_verification_code,
    verify_code,
    send_verification_email,
    send_verification_sms,
)

__all__ = [
    "create_access_token",
    "verify_access_token",
    "get_current_user",
    "oauth2_scheme",
    "Role",
    "Permission",
    "check_permission",
    "require_permission",
    "encrypt_data",
    "decrypt_data",
    "encrypt_file",
    "decrypt_file",
    "detect_pii",
    "redact_pii",
    "anonymize_data",
    "generate_verification_code",
    "verify_code",
    "send_verification_email",
    "send_verification_sms",
]
