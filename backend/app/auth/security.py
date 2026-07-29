"""Security utilities for API key hashing and validation."""

from datetime import datetime, timezone
from passlib.hash import bcrypt


def hash_api_key(api_key: str) -> str:
    """
    Hash an API key using bcrypt.
    
    Args:
        api_key: The plain text API key
        
    Returns:
        The hashed API key
    """
    return bcrypt.hash(api_key)


def verify_api_key(plain_key: str, hashed_key: str) -> bool:
    """
    Verify a plain API key against a hashed key.
    
    Args:
        plain_key: The plain text API key
        hashed_key: The stored hashed key
        
    Returns:
        True if the key matches, False otherwise
    """
    try:
        return bcrypt.verify(plain_key, hashed_key)
    except Exception:
        return False


def is_api_key_expired(expires_at: datetime | None) -> bool:
    """
    Check if an API key has expired.
    
    Args:
        expires_at: The expiration datetime (UTC)
        
    Returns:
        True if expired, False if still valid or no expiration
    """
    if expires_at is None:
        return False
    
    return datetime.now(timezone.utc) >= expires_at
