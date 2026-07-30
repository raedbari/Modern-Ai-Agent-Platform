"""Idempotency key handling to prevent duplicate message processing."""

from typing import Optional

from sqlalchemy.orm import Session

from backend.app.db.models import Message


class IdempotencyViolation(Exception):
    """Raised when an idempotency key has already been used."""

    def __init__(self, existing_message: Message):
        self.existing_message = existing_message
        super().__init__(f"Idempotency key already used: {existing_message.idempotency_key}")


def check_idempotency_key(
    db: Session,
    idempotency_key: Optional[str],
) -> Optional[Message]:
    """
    Check if an idempotency key has been used before.
    
    Args:
        db: Database session
        idempotency_key: The idempotency key from the request
        
    Returns:
        Existing message if idempotency key was used, None otherwise
        
    Raises:
        IdempotencyViolation: If key exists with different content
    """
    if not idempotency_key:
        return None
    
    existing_message = (
        db.query(Message)
        .filter(Message.idempotency_key == idempotency_key)
        .first()
    )
    
    return existing_message
