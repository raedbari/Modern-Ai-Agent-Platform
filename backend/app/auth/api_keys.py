"""High-entropy API-key generation and verification helpers."""

from dataclasses import dataclass, field
import hashlib
import secrets

API_KEY_PREFIX = "maap_"
KEY_ID_BYTES = 12
SECRET_BYTES = 32


@dataclass(frozen=True, slots=True)
class IssuedApiKey:
    """A newly issued credential; the raw key must be shown only once."""

    key_id: str
    raw_key: str = field(repr=False)
    key_digest: str


def hash_api_key_secret(secret: str) -> str:
    """Hash one high-entropy API-key secret for database storage."""

    return hashlib.sha256(secret.encode("utf-8")).hexdigest()


def issue_api_key() -> IssuedApiKey:
    """Create a key identifier, raw credential, and storable digest."""

    key_id = secrets.token_urlsafe(KEY_ID_BYTES)
    secret = secrets.token_urlsafe(SECRET_BYTES)
    return IssuedApiKey(
        key_id=key_id,
        raw_key=f"{API_KEY_PREFIX}{key_id}.{secret}",
        key_digest=hash_api_key_secret(secret),
    )


def parse_api_key(raw_key: str) -> tuple[str, str] | None:
    """Split a raw API key into its public identifier and secret."""

    if not raw_key.startswith(API_KEY_PREFIX):
        return None

    key_id, separator, secret = raw_key[len(API_KEY_PREFIX):].partition(".")
    if (
        separator != "."
        or not key_id
        or len(key_id) > 64
        or not secret
    ):
        return None

    return key_id, secret


def verify_api_key_secret(secret: str, expected_digest: str) -> bool:
    """Compare a presented secret to the stored digest in constant time."""

    actual_digest = hash_api_key_secret(secret)
    return secrets.compare_digest(actual_digest, expected_digest)