"""
Project Entity for Project Management Application

Represents a project container for organizing work, managing team members,
and tracking progress as specified in functional requirements.
"""

from datetime import datetime, timezone
from typing import Any, ClassVar, Dict, List, Optional

from pydantic import ConfigDict, Field, field_validator, model_validator

from common.entity.cyoda_entity import CyodaEntity


class Project(CyodaEntity):
    """
    Project entity represents a main project container for organizing work.
    
    Inherits from CyodaEntity to get common fields like entity_id, state, etc.
    The state field manages workflow states: initial_state -> created -> active -> completed
    """

    # Entity constants
    ENTITY_NAME: ClassVar[str] = "Project"
    ENTITY_VERSION: ClassVar[int] = 1

    # Required fields from functional requirements
    name: str = Field(..., description="Project name")
    description: str = Field(..., description="Project description")
    status: str = Field(
        default="PLANNING",
        description="Project status (PLANNING, ACTIVE, ON_HOLD, COMPLETED, CANCELLED)"
    )
    owner_id: str = Field(..., alias="ownerId", description="Project owner user ID")
    
    # Optional fields
    start_date: Optional[str] = Field(
        default=None,
        alias="startDate", 
        description="Project start date (ISO 8601 format)"
    )
    end_date: Optional[str] = Field(
        default=None,
        alias="endDate",
        description="Project end date (ISO 8601 format)"
    )
    team_members: Optional[List[str]] = Field(
        default_factory=list,
        alias="teamMembers",
        description="List of user IDs assigned to project"
    )
    priority: str = Field(
        default="MEDIUM",
        description="Project priority (LOW, MEDIUM, HIGH, CRITICAL)"
    )
    budget: Optional[float] = Field(
        default=None,
        description="Project budget"
    )

    # Timestamps (inherited created_at from CyodaEntity)
    created_at: Optional[str] = Field(
        default_factory=lambda: datetime.now(timezone.utc)
        .isoformat()
        .replace("+00:00", "Z"),
        alias="createdAt",
        description="Timestamp when the project was created (ISO 8601 format)",
    )
    updated_at: Optional[str] = Field(
        default=None,
        alias="updatedAt",
        description="Timestamp when the project was last updated (ISO 8601 format)",
    )

    # Validation constants
    ALLOWED_STATUSES: ClassVar[List[str]] = [
        "PLANNING", "ACTIVE", "ON_HOLD", "COMPLETED", "CANCELLED"
    ]
    ALLOWED_PRIORITIES: ClassVar[List[str]] = [
        "LOW", "MEDIUM", "HIGH", "CRITICAL"
    ]

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate project name according to requirements"""
        if not v or len(v.strip()) == 0:
            raise ValueError("Project name must be non-empty")
        if len(v) < 3:
            raise ValueError("Project name must be at least 3 characters long")
        if len(v) > 100:
            raise ValueError("Project name must be at most 100 characters long")
        return v.strip()

    @field_validator("description")
    @classmethod
    def validate_description(cls, v: str) -> str:
        """Validate project description according to requirements"""
        if not v or len(v.strip()) == 0:
            raise ValueError("Project description must be non-empty")
        if len(v) > 1000:
            raise ValueError("Project description must be at most 1000 characters long")
        return v.strip()

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        """Validate project status"""
        if v not in cls.ALLOWED_STATUSES:
            raise ValueError(f"Status must be one of: {cls.ALLOWED_STATUSES}")
        return v

    @field_validator("priority")
    @classmethod
    def validate_priority(cls, v: str) -> str:
        """Validate project priority"""
        if v not in cls.ALLOWED_PRIORITIES:
            raise ValueError(f"Priority must be one of: {cls.ALLOWED_PRIORITIES}")
        return v

    @field_validator("owner_id")
    @classmethod
    def validate_owner_id(cls, v: str) -> str:
        """Validate owner ID is not empty"""
        if not v or len(v.strip()) == 0:
            raise ValueError("Owner ID must be provided")
        return v.strip()

    @field_validator("budget")
    @classmethod
    def validate_budget(cls, v: Optional[float]) -> Optional[float]:
        """Validate budget is positive if provided"""
        if v is not None and v < 0:
            raise ValueError("Budget must be positive")
        return v

    @model_validator(mode="after")
    def validate_business_logic(self) -> "Project":
        """Validate business logic rules"""
        # Validate date consistency
        if self.start_date and self.end_date:
            try:
                start = datetime.fromisoformat(self.start_date.replace("Z", "+00:00"))
                end = datetime.fromisoformat(self.end_date.replace("Z", "+00:00"))
                if end <= start:
                    raise ValueError("End date must be after start date")
            except ValueError as e:
                if "End date must be after start date" in str(e):
                    raise
                raise ValueError("Invalid date format. Use ISO 8601 format")

        return self

    def update_timestamp(self) -> None:
        """Update the updated_at timestamp to current time"""
        self.updated_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    def add_team_member(self, user_id: str) -> None:
        """Add a team member to the project"""
        if not self.team_members:
            self.team_members = []
        if user_id not in self.team_members:
            self.team_members.append(user_id)
            self.update_timestamp()

    def remove_team_member(self, user_id: str) -> None:
        """Remove a team member from the project"""
        if self.team_members and user_id in self.team_members:
            self.team_members.remove(user_id)
            self.update_timestamp()

    def is_active(self) -> bool:
        """Check if project is in active status"""
        return self.status == "ACTIVE"

    def is_completed(self) -> bool:
        """Check if project is completed"""
        return self.status == "COMPLETED"

    def can_be_modified(self) -> bool:
        """Check if project can be modified (not completed or cancelled)"""
        return self.status not in ["COMPLETED", "CANCELLED"]

    def to_api_response(self) -> Dict[str, Any]:
        """Convert to API response format"""
        data = self.model_dump(by_alias=True)
        # Add state for API compatibility
        data["state"] = self.state
        return data

    model_config = ConfigDict(
        populate_by_name=True,
        use_enum_values=True,
        validate_assignment=True,
        extra="allow",
    )
