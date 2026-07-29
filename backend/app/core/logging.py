"""Structured logging configuration."""

import logging
import sys
from typing import Any

logger = logging.getLogger("maap")
logger.setLevel(logging.INFO)

# Console handler with structured format
handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.INFO)

# Simple structured format (in production use JSON formatter)
formatter = logging.Formatter(
    '{"time": "%(asctime)s", "level": "%(levelname)s", "logger": "%(name)s", "message": "%(message)s"}'
)
handler.setFormatter(formatter)

logger.addHandler(handler)


def log_request(
    request_id: str,
    client_id: str,
    endpoint: str,
    method: str,
    **kwargs: Any,
) -> None:
    """
    Log an API request with structured data.
    
    NEVER log full message content or API keys.
    """
    log_data = {
        "request_id": request_id,
        "client_id": client_id,
        "endpoint": endpoint,
        "method": method,
        **kwargs,
    }
    
    # Remove sensitive fields
    log_data.pop("api_key", None)
    log_data.pop("message_content", None)
    
    logger.info(f"API Request: {log_data}")


def log_error(
    request_id: str,
    error_type: str,
    error_message: str,
    **kwargs: Any,
) -> None:
    """
    Log an error with structured data.
    
    NEVER log tracebacks or database details that could leak to users.
    """
    log_data = {
        "request_id": request_id,
        "error_type": error_type,
        "error_message": error_message,
        **kwargs,
    }
    
    logger.error(f"Error: {log_data}")
