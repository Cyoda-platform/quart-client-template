"""
User entity for claims platform users.

Represents users with different roles (Claimant, Adjuster, Handler, Admin).
"""

from datetime import datetime, timezone
from typing import Any, ClassVar, Dict, Optional

from pydantic import ConfigDict, Field, field_validator, model_validator

from common.entity.cyoda_entity import CyodaEntity


class User(CyodaEntity):
    """
    User represents a platform user with role-based access.

    Supports roles: Claimant, Adjuster, Claims Handler, Admin.
    """

    ENTITY_NAME: ClassVar[str] = "User"
    ENTITY_VERSION: ClassVar[int] = 1

    email: str = Field(..., alias="email", description="User email address")
    first_name: str = Field(..., alias="firstName", description="First name")
    last_name: str = Field(..., alias="lastName", description="Last name")
    phone_number: Optional[str] = Field(
        default=None, alias="phoneNumber", description="Phone number"
    )
    role: str = Field(..., alias="role", description="User role")
    status: str = Field(default="ACTIVE", alias="status", description="User status")
    organization_id: Optional[str] = Field(
        default=None, alias="organizationId", description="Organization ID if applicable"
    )
    department: Optional[str] = Field(default=None, description="Department")
    is_verified: bool = Field(
        default=False, alias="isVerified", description="Email verification status"
    )
    last_login: Optional[str] = Field(
        default=None, alias="lastLogin", description="Last login timestamp"
    )
    created_at: Optional[str] = Field(
        default_factory=lambda: datetime.now(timezone.utc)
        .isoformat()
        .replace("+00:00", "Z"),
        alias="createdAt",
        description="Timestamp when the user was created (ISO 8601 format)",
    )
    updated_at: Optional[str] = Field(
        default=None,
        alias="updatedAt",
        description="Timestamp when the user was last updated (ISO 8601 format)",
    )

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

    @model_validator(mode="after")
    def validate_business_logic(self) -> "User":
        """Validate business logic rules"""
        if "@" not in self.email:
            raise ValueError("Invalid email address")
        return self

    def update_timestamp(self) -> None:
        """Update the updated_at timestamp to current time"""
        self.updated_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    def to_api_response(self) -> Dict[str, Any]:
        """Convert to API response format"""
        data = self.model_dump(by_alias=True)
        data["state"] = self.state
        return data

    model_config = ConfigDict(
        populate_by_name=True,
        use_enum_values=True,
        validate_assignment=True,
        extra="allow",
    )

