"""
Project Entity for Project Management Application

Represents projects that contain tasks and have team members.
Projects are owned by managers/admins and can have multiple member users.
"""

from datetime import datetime, timezone
from typing import Any, ClassVar, Dict, List, Optional

from pydantic import ConfigDict, Field, field_validator, model_validator

from common.entity.cyoda_entity import CyodaEntity


class Project(CyodaEntity):
    """
    Project entity represents containers for tasks with team members.
    
    Projects are owned by users with MANAGER or ADMIN roles and can contain
    multiple tasks and team members. State managed by workflow: 
    initial_state -> created -> active -> (completed/archived).
    """

    # Entity constants
    ENTITY_NAME: ClassVar[str] = "Project"
    ENTITY_VERSION: ClassVar[int] = 1

    # Core project fields
    project_id: str = Field(..., description="Business identifier for the project")
    name: str = Field(..., description="Project name")
    description: str = Field(..., description="Project description")
    owner_id: str = Field(..., description="Technical ID of the project owner (User)")
    members: Optional[List[str]] = Field(
        default_factory=list,
        description="List of user technical IDs who are project members"
    )
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

    # Timestamps
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

    @field_validator("project_id")
    @classmethod
    def validate_project_id(cls, v: str) -> str:
        """Validate project_id field"""
        if not v or len(v.strip()) == 0:
            raise ValueError("Project ID must be non-empty")
        if len(v) < 3:
            raise ValueError("Project ID must be at least 3 characters long")
        if len(v) > 50:
            raise ValueError("Project ID must be at most 50 characters long")
        return v.strip()

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate name field"""
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
        """Validate description field"""
        if not v or len(v.strip()) == 0:
            raise ValueError("Project description must be non-empty")
        if len(v) > 1000:
            raise ValueError("Project description must be at most 1000 characters long")
        return v.strip()

    @field_validator("owner_id")
    @classmethod
    def validate_owner_id(cls, v: str) -> str:
        """Validate owner_id field"""
        if not v or len(v.strip()) == 0:
            raise ValueError("Owner ID must be non-empty")
        return v.strip()

    @field_validator("members")
    @classmethod
    def validate_members(cls, v: Optional[List[str]]) -> List[str]:
        """Validate members field"""
        if v is None:
            return []
        
        # Remove duplicates and empty strings
        cleaned_members = []
        for member_id in v:
            if member_id and member_id.strip():
                member_id = member_id.strip()
                if member_id not in cleaned_members:
                    cleaned_members.append(member_id)
        
        return cleaned_members

    @field_validator("start_date")
    @classmethod
    def validate_start_date(cls, v: Optional[str]) -> Optional[str]:
        """Validate start_date field"""
        if v is None:
            return None
        
        if not v.strip():
            return None
            
        # Basic ISO 8601 format validation
        try:
            datetime.fromisoformat(v.replace('Z', '+00:00'))
        except ValueError:
            raise ValueError("Start date must be in ISO 8601 format")
        
        return v.strip()

    @field_validator("end_date")
    @classmethod
    def validate_end_date(cls, v: Optional[str]) -> Optional[str]:
        """Validate end_date field"""
        if v is None:
            return None
        
        if not v.strip():
            return None
            
        # Basic ISO 8601 format validation
        try:
            datetime.fromisoformat(v.replace('Z', '+00:00'))
        except ValueError:
            raise ValueError("End date must be in ISO 8601 format")
        
        return v.strip()

    @model_validator(mode="after")
    def validate_business_logic(self) -> "Project":
        """Validate business logic rules"""
        # Validate date range if both dates are provided
        if self.start_date and self.end_date:
            try:
                start_dt = datetime.fromisoformat(self.start_date.replace('Z', '+00:00'))
                end_dt = datetime.fromisoformat(self.end_date.replace('Z', '+00:00'))
                
                if end_dt <= start_dt:
                    raise ValueError("End date must be after start date")
            except ValueError as e:
                if "End date must be after start date" in str(e):
                    raise e
                # If date parsing fails, let the field validators handle it
        
        return self

    def update_timestamp(self) -> None:
        """Update the updated_at timestamp to current time"""
        self.updated_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    def add_member(self, user_id: str) -> None:
        """Add a member to the project"""
        if user_id and user_id not in (self.members or []):
            if self.members is None:
                self.members = []
            self.members.append(user_id)
            self.update_timestamp()

    def remove_member(self, user_id: str) -> None:
        """Remove a member from the project"""
        if self.members and user_id in self.members:
            self.members.remove(user_id)
            self.update_timestamp()

    def is_member(self, user_id: str) -> bool:
        """Check if user is a project member"""
        return user_id in (self.members or []) or user_id == self.owner_id

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
