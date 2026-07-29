"""FastAPI dependencies for authentication and authorization."""

from datetime import datetime, timezone
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.models import AuthenticatedContext
from backend.app.auth.security import verify_api_key
from backend.app.db import get_db
from backend.app.db.models import ApiKey, Tenant


async def get_authenticated_context(
    x_api_key: Annotated[str, Header(description="API Key for authentication")],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AuthenticatedContext:
    """
    FastAPI dependency that extracts and verifies the API key from headers.
    
    Security rules:
    - Extracts key from X-API-Key header
    - Hashes the key and compares with stored hash
    - Verifies the tenant is active
    - Verifies the key is active and not expired
    - Updates last_used_at timestamp
    - Never logs the plain API key
    
    Args:
        x_api_key: The API key from X-API-Key header
        db: Database session
        
    Returns:
        AuthenticatedContext with tenant_id and key metadata
        
    Raises:
        HTTPException(401): If authentication fails for any reason
    """
    # Query all active API keys to verify against
    # We cannot query by hash directly because we need to check all keys
    # This is a security tradeoff - we accept the performance cost
    result = await db.execute(
        select(ApiKey, Tenant)
        .join(Tenant, ApiKey.tenant_id == Tenant.id)
        .where(ApiKey.is_active == True)
        .where(Tenant.is_active == True)
    )
    
    api_keys = result.all()
    
    # Try to verify against each active key
    matched_key: ApiKey | None = None
    matched_tenant: Tenant | None = None
    
    for api_key, tenant in api_keys:
        # Check if key is expired
        if api_key.expires_at and api_key.expires_at < datetime.now(timezone.utc):
            continue
            
        # Verify the key hash
        if verify_api_key(x_api_key, api_key.key_hash):
            matched_key = api_key
            matched_tenant = tenant
            break
    
    # If no match found, return generic error
    # Do not reveal whether the key exists or is invalid
    if not matched_key or not matched_tenant:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    
    # Update last_used_at timestamp asynchronously
    # Don't wait for this to complete
    await db.execute(
        update(ApiKey)
        .where(ApiKey.id == matched_key.id)
        .values(last_used_at=datetime.now(timezone.utc))
    )
    await db.commit()
    
    # Return authenticated context
    return AuthenticatedContext(
        tenant_id=matched_tenant.id,
        api_key_id=matched_key.id,
        api_key_name=matched_key.name,
    )
