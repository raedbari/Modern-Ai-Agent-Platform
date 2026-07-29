"""FastAPI dependencies for authentication and tenant context."""

from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.auth.security import is_api_key_expired, verify_api_key
from backend.app.core.config import Settings, get_settings
from backend.app.db.base import get_db
from backend.app.db.models import ApiKey, Client


class TenantContext:
    """
    Authenticated tenant context extracted from API key.
    This is the ONLY trusted source of client_id in the system.
    """

    def __init__(self, client_id: str, client_name: str):
        self.client_id = client_id
        self.client_name = client_name

    def __repr__(self) -> str:
        return f"TenantContext(client_id={self.client_id}, client_name={self.client_name})"


async def extract_api_key(
    x_api_key: Annotated[str | None, Header()] = None,
    settings: Settings = Depends(get_settings),
) -> str:
    """
    Extract API key from request header.
    
    Raises:
        HTTPException: 401 if API key is missing
    """
    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key is required",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    
    return x_api_key


async def get_tenant_context(
    api_key: Annotated[str, Depends(extract_api_key)],
    db: Session = Depends(get_db),
) -> TenantContext:
    """
    Authenticate API key and return trusted tenant context.
    
    This dependency:
    1. Hashes the provided API key
    2. Looks up the hash in database
    3. Validates the key is active and not expired
    4. Returns authenticated TenantContext
    
    NEVER accept client_id from user input - only from this dependency.
    
    Raises:
        HTTPException: 401 if authentication fails
    """
    # Find all active API keys and verify against hashes
    # We cannot query by hash directly since we need to verify each one
    api_keys = (
        db.query(ApiKey)
        .filter(ApiKey.is_active == True)  # noqa: E712
        .all()
    )
    
    authenticated_key = None
    for key_record in api_keys:
        if verify_api_key(api_key, key_record.key_hash):
            authenticated_key = key_record
            break
    
    if not authenticated_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    
    # Check if key is expired
    if is_api_key_expired(authenticated_key.expires_at):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key has expired",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    
    # Get client information
    client = db.query(Client).filter(Client.id == authenticated_key.client_id).first()
    
    if not client:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Client not found",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    
    if not client.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Client account is disabled",
        )
    
    # Update last used timestamp (async in production, but OK for now)
    authenticated_key.last_used_at = datetime.now(timezone.utc)
    db.commit()
    
    return TenantContext(
        client_id=client.id,
        client_name=client.name,
    )


# Type alias for dependency injection
from datetime import datetime, timezone

AuthenticatedClient = Annotated[TenantContext, Depends(get_tenant_context)]
