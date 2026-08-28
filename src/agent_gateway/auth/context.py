"""Authentication context models."""

from enum import StrEnum

from pydantic import BaseModel, Field


class Role(StrEnum):
    """Demo API roles."""

    EMPLOYEE = "employee"
    ANALYST = "analyst"
    FACILITIES_MANAGER = "facilities_manager"
    PLATFORM_ADMIN = "platform_admin"


class AuthContext(BaseModel):
    """Authenticated caller context derived from API key."""

    subject: str = Field(description="Principal identifier for the caller.")
    tenant_id: str = Field(description="Tenant scope enforced on all data access.")
    role: Role = Field(description="Role used for tool authorization.")
