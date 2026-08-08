from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

ApplicationStatus = Literal[
    "email_pending", "under_review", "changes_requested", "approved", "rejected"
]

class SignupRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=255)
    email: str = Field(min_length=3, max_length=320)
    company_name: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=12, max_length=128)
    requested_plan: str = Field(min_length=1, max_length=64)
    legal_accepted: Literal[True]

    @field_validator("name", "company_name", "requested_plan")
    @classmethod
    def strip_required(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Value must not be blank.")
        return value

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        value = value.strip()
        if value.count("@") != 1 or " " in value:
            raise ValueError("A valid email address is required.")
        local, domain = value.rsplit("@", 1)
        if not local or "." not in domain:
            raise ValueError("A valid email address is required.")
        return value

class SignupResponse(BaseModel):
    status: ApplicationStatus
    email_verification_required: bool = True
    verification_token: str | None = None

class VerifyEmailRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    token: str = Field(min_length=20, max_length=512)

class VerifyEmailResponse(BaseModel):
    email_verified: bool
    status: ApplicationStatus

class ApprovalRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    review_note: str | None = Field(default=None, max_length=2000)

class TenantApplicationResponse(BaseModel):
    id: str
    user_id: str
    applicant_name: str
    applicant_email: str
    email_verified: bool
    company_name: str
    requested_plan: str
    status: ApplicationStatus
    submitted_at: datetime | None
    reviewed_at: datetime | None
    reviewed_by: str | None
    review_note: str | None
    approved_tenant_id: str | None
    created_at: datetime
    updated_at: datetime
