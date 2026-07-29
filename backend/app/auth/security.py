"""Security utilities for API key hashing and verification."""

from passlib.context import CryptContext

# Use bcrypt for hashing API keys
# Bcrypt is deliberately slow to make brute-force attacks harder
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_api_key(plain_key: str) -> str:
    """
    Hash an API key using bcrypt.
    
    Args:
        plain_key: The plain text API key
        
    Returns:
        The bcrypt hash of the key
        
    Note:
        This is a one-way operation. The plain key cannot be recovered.
    """
    return pwd_context.hash(plain_key)


def verify_api_key(plain_key: str, hashed_key: str) -> bool:
    """
    Verify a plain API key against its stored hash.
    
    Args:
        plain_key: The plain text API key to verify
        hashed_key: The stored bcrypt hash
        
    Returns:
        True if the key matches, False otherwise
    """
    return pwd_context.verify(plain_key, hashed_key)
