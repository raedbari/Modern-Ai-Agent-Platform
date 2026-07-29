"""Authentication data models."""

from pydantic import BaseModel, ConfigDict


class AuthenticatedContext(BaseModel):
    """
    Context returned after successful API key authentication.
    
    Contains the authenticated tenant_id and optionally the API key metadata.
    """

    model_config = ConfigDict(frozen=True)

    tenant_id: str
    api_key_id: int
    api_key_name: str
