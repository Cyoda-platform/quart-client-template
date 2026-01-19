"""
User entity for claims platform users.

Represents users with different roles (Claimant, Adjuster, Handler, Admin).
"""

from datetime import datetime, timezone
from typing import ClassVar, Optional

from pydantic import Field, field_validator

from common.entity.cyoda_entity import CyodaEntity


class User(CyodaEntity):
    """
    User represents a platform user with role-based access.
    
    Supports roles: Claimant, Adjuster, Claims Handler, Admin.
    """

    ENTITY_NAME: ClassVar[str] = "User"
    ENTITY_VERSION: ClassVar[int] = 1

    email: str = Field(..., description="User email address")
    first_name: str = Field(..., description="First name")
    last_name: str = Field(..., description="Last name")
    phone_number: Optional[str] = Field(default=None, description="Phone number")
    role: str = Field(..., description="User role")
    status: str = Field(default="ACTIVE", description="User status")
    organization_id: Optional[str] = Field(
        default=None, description="Organization ID if applicable"
    )
    department: Optional[str] = Field(default=None, description="Department")
    is_verified: bool = Field(default=False, description="Email verification status")
    last_login: Optional[str] = Field(default=None, description="Last login timestamp")

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        allowed = ["Claimant", "Adjuster", "Claims Handler", "Admin"]
        if v not in allowed:
            raise ValueError(f"Role must be one of {allowed}")
        return v

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        allowed = ["ACTIVE", "INACTIVE", "SUSPENDED"]
        if v not in allowed:
            raise ValueError(f"Status must be one of {allowed}")
        return v

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        if "@" not in v:
            raise ValueError("Invalid email address")
        return v

