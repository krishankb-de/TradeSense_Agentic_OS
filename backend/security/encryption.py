"""AES-256 encryption for sensitive data at rest."""

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import padding
import os
import base64
from typing import Union


# AES-256 requires 32-byte key
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY", "").encode()
if not ENCRYPTION_KEY or len(ENCRYPTION_KEY) != 32:
    # Generate a random key if not provided (for development only)
    ENCRYPTION_KEY = os.urandom(32)
    print("WARNING: Using random encryption key. Set ENCRYPTION_KEY environment variable in production.")


def encrypt_data(plaintext: Union[str, bytes]) -> str:
    """
    Encrypt data using AES-256-CBC.
    
    Args:
        plaintext: Data to encrypt (string or bytes)
        
    Returns:
        Base64-encoded encrypted data with IV prepended
    """
    # Convert string to bytes if needed
    if isinstance(plaintext, str):
        plaintext = plaintext.encode('utf-8')
    
    # Generate random IV (16 bytes for AES)
    iv = os.urandom(16)
    
    # Create cipher
    cipher = Cipher(
        algorithms.AES(ENCRYPTION_KEY),
        modes.CBC(iv),
        backend=default_backend()
    )
    encryptor = cipher.encryptor()
    
    # Pad plaintext to block size (128 bits = 16 bytes)
    padder = padding.PKCS7(128).padder()
    padded_data = padder.update(plaintext) + padder.finalize()
    
    # Encrypt
    ciphertext = encryptor.update(padded_data) + encryptor.finalize()
    
    # Prepend IV to ciphertext and encode as base64
    encrypted = iv + ciphertext
    return base64.b64encode(encrypted).decode('utf-8')


def decrypt_data(encrypted_data: str) -> str:
    """
    Decrypt AES-256-CBC encrypted data.
    
    Args:
        encrypted_data: Base64-encoded encrypted data with IV prepended
        
    Returns:
        Decrypted plaintext string
    """
    # Decode from base64
    encrypted = base64.b64decode(encrypted_data.encode('utf-8'))
    
    # Extract IV (first 16 bytes)
    iv = encrypted[:16]
    ciphertext = encrypted[16:]
    
    # Create cipher
    cipher = Cipher(
        algorithms.AES(ENCRYPTION_KEY),
        modes.CBC(iv),
        backend=default_backend()
    )
    decryptor = cipher.decryptor()
    
    # Decrypt
    padded_plaintext = decryptor.update(ciphertext) + decryptor.finalize()
    
    # Unpad
    unpadder = padding.PKCS7(128).unpadder()
    plaintext = unpadder.update(padded_plaintext) + unpadder.finalize()
    
    return plaintext.decode('utf-8')


def encrypt_file(input_path: str, output_path: str) -> None:
    """
    Encrypt a file using AES-256-CBC.
    
    Args:
        input_path: Path to plaintext file
        output_path: Path to save encrypted file
    """
    with open(input_path, 'rb') as f:
        plaintext = f.read()
    
    encrypted = encrypt_data(plaintext)
    
    with open(output_path, 'w') as f:
        f.write(encrypted)


def decrypt_file(input_path: str, output_path: str) -> None:
    """
    Decrypt an AES-256-CBC encrypted file.
    
    Args:
        input_path: Path to encrypted file
        output_path: Path to save decrypted file
    """
    with open(input_path, 'r') as f:
        encrypted_data = f.read()
    
    plaintext = decrypt_data(encrypted_data)
    
    with open(output_path, 'w') as f:
        f.write(plaintext)


def encrypt_pii_fields(data: dict, fields: list[str]) -> dict:
    """
    Encrypt specific PII fields in a dictionary.
    
    Args:
        data: Dictionary containing data
        fields: List of field names to encrypt
        
    Returns:
        Dictionary with specified fields encrypted
    """
    encrypted_data = data.copy()
    
    for field in fields:
        if field in encrypted_data and encrypted_data[field]:
            encrypted_data[field] = encrypt_data(str(encrypted_data[field]))
    
    return encrypted_data


def decrypt_pii_fields(data: dict, fields: list[str]) -> dict:
    """
    Decrypt specific PII fields in a dictionary.
    
    Args:
        data: Dictionary containing encrypted data
        fields: List of field names to decrypt
        
    Returns:
        Dictionary with specified fields decrypted
    """
    decrypted_data = data.copy()
    
    for field in fields:
        if field in decrypted_data and decrypted_data[field]:
            try:
                decrypted_data[field] = decrypt_data(decrypted_data[field])
            except Exception:
                # If decryption fails, leave as is (might not be encrypted)
                pass
    
    return decrypted_data
