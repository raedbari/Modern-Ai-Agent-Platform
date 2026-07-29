"""Rate limiting implementation using slowapi."""

from slowapi import Limiter
from slowapi.util import get_remote_address

from backend.app.core.config import get_settings

settings = get_settings()


def get_api_key_identifier(request) -> str:
    """
    Extract API key from request for rate limiting.
    Falls back to IP address if no API key present.
    """
    api_key = request.headers.get("X-API-Key", "")
    if api_key:
        # Use first 16 chars of API key as identifier (don't log full key)
        return f"apikey:{api_key[:16]}"
    return get_remote_address(request)


# Initialize rate limiter
limiter = Limiter(
    key_func=get_api_key_identifier,
    default_limits=[f"{settings.rate_limit_per_minute}/minute"],
    storage_uri="memory://",
)
