"""
User Entity for Project Management Application

Represents system users with role-based access control and profile information.
Supports ADMIN, MANAGER, and MEMBER roles with different permission levels.
"""

from datetime import datetime, timezone
from typing import Any, ClassVar, Dict, List, Optional

from pydantic import ConfigDict, Field, field_validator, model_validator

from common.entity.cyoda_entity import CyodaEntity


class User(CyodaEntity):
    """
    User entity represents system users with role-based access control.
    
    Manages user profiles, authentication, and permission levels for the
    project management system. State managed by workflow: initial_state -> active.
    """

    # Entity constants
    ENTITY_NAME: ClassVar[str] = "User"
    ENTITY_VERSION: ClassVar[int] = 1

    # Core user fields
    user_id: str = Field(..., description="Business identifier for the user")
    name: str = Field(..., description="Full name of the user")
    email: str = Field(..., description="Email address (must be unique)")
    role: str = Field(..., description="User role: ADMIN, MANAGER, MEMBER")
    is_active: Optional[bool] = Field(
        default=True,
        alias="isActive",
        description="Whether user account is active"
    )

    # Timestamps
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

    # Role constants
    ALLOWED_ROLES: ClassVar[List[str]] = ["ADMIN", "MANAGER", "MEMBER"]

    @field_validator("user_id")
    @classmethod
    def validate_user_id(cls, v: str) -> str:
        """Validate user_id field"""
        if not v or len(v.strip()) == 0:
            raise ValueError("User ID must be non-empty")
        if len(v) < 3:
            raise ValueError("User ID must be at least 3 characters long")
        if len(v) > 50:
            raise ValueError("User ID must be at most 50 characters long")
        return v.strip()

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate name field"""
        if not v or len(v.strip()) == 0:
            raise ValueError("Name must be non-empty")
        if len(v) < 2:
            raise ValueError("Name must be at least 2 characters long")
        if len(v) > 100:
            raise ValueError("Name must be at most 100 characters long")
        return v.strip()

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        """Validate email field"""
        if not v or len(v.strip()) == 0:
            raise ValueError("Email must be non-empty")
        
        email = v.strip().lower()
        
        # Basic email validation
        if "@" not in email or "." not in email:
            raise ValueError("Email must be a valid email address")
        
        if len(email) > 255:
            raise ValueError("Email must be at most 255 characters long")
            
        return email

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        """Validate role field"""
        if v not in cls.ALLOWED_ROLES:
            raise ValueError(f"Role must be one of: {cls.ALLOWED_ROLES}")
        return v

    @model_validator(mode="after")
    def validate_business_logic(self) -> "User":
        """Validate business logic rules"""
        # Additional business rules can be added here
        return self

    def update_timestamp(self) -> None:
        """Update the updated_at timestamp to current time"""
        self.updated_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    def is_admin(self) -> bool:
        """Check if user has admin role"""
        return self.role == "ADMIN"

    def is_manager(self) -> bool:
        """Check if user has manager role"""
        return self.role == "MANAGER"

    def is_member(self) -> bool:
        """Check if user has member role"""
        return self.role == "MEMBER"

    def can_manage_users(self) -> bool:
        """Check if user can manage other users"""
        return self.role == "ADMIN"

    def can_manage_projects(self) -> bool:
        """Check if user can manage projects"""
        return self.role in ["ADMIN", "MANAGER"]

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
