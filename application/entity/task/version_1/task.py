"""
Task Entity for Project Management Application

Represents individual work items within projects with assignment,
deadlines, priorities, and status tracking as specified in functional requirements.
"""

from datetime import datetime, timezone
from typing import Any, ClassVar, Dict, List, Optional

from pydantic import ConfigDict, Field, field_validator, model_validator

from common.entity.cyoda_entity import CyodaEntity


class Task(CyodaEntity):
    """
    Task entity represents individual work items within projects.
    
    Inherits from CyodaEntity to get common fields like entity_id, state, etc.
    The state field manages workflow states: initial_state -> created -> assigned -> in_progress -> completed
    """

    # Entity constants
    ENTITY_NAME: ClassVar[str] = "Task"
    ENTITY_VERSION: ClassVar[int] = 1

    # Required fields from functional requirements
    title: str = Field(..., description="Task title")
    project_id: str = Field(..., alias="projectId", description="Parent project ID")
    reporter_id: str = Field(..., alias="reporterId", description="Task creator user ID")
    
    # Optional fields
    description: Optional[str] = Field(
        default="",
        description="Task description"
    )
    assignee_id: Optional[str] = Field(
        default=None,
        alias="assigneeId",
        description="Assigned user ID"
    )
    status: str = Field(
        default="TODO",
        description="Task status (TODO, IN_PROGRESS, IN_REVIEW, DONE, CANCELLED)"
    )
    priority: str = Field(
        default="MEDIUM",
        description="Task priority (LOW, MEDIUM, HIGH, CRITICAL)"
    )
    due_date: Optional[str] = Field(
        default=None,
        alias="dueDate",
        description="Task deadline (ISO 8601 format)"
    )
    estimated_hours: Optional[float] = Field(
        default=None,
        alias="estimatedHours",
        description="Estimated work hours"
    )
    actual_hours: Optional[float] = Field(
        default=None,
        alias="actualHours",
        description="Actual work hours"
    )
    tags: Optional[List[str]] = Field(
        default_factory=list,
        description="List of tags for categorization"
    )

    # Timestamps (inherited created_at from CyodaEntity)
    created_at: Optional[str] = Field(
        default_factory=lambda: datetime.now(timezone.utc)
        .isoformat()
        .replace("+00:00", "Z"),
        alias="createdAt",
        description="Timestamp when the task was created (ISO 8601 format)",
    )
    updated_at: Optional[str] = Field(
        default=None,
        alias="updatedAt",
        description="Timestamp when the task was last updated (ISO 8601 format)",
    )

    # Validation constants
    ALLOWED_STATUSES: ClassVar[List[str]] = [
        "TODO", "IN_PROGRESS", "IN_REVIEW", "DONE", "CANCELLED"
    ]
    ALLOWED_PRIORITIES: ClassVar[List[str]] = [
        "LOW", "MEDIUM", "HIGH", "CRITICAL"
    ]

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str) -> str:
        """Validate task title according to requirements"""
        if not v or len(v.strip()) == 0:
            raise ValueError("Task title must be non-empty")
        if len(v) < 3:
            raise ValueError("Task title must be at least 3 characters long")
        if len(v) > 200:
            raise ValueError("Task title must be at most 200 characters long")
        return v.strip()

    @field_validator("description")
    @classmethod
    def validate_description(cls, v: Optional[str]) -> Optional[str]:
        """Validate task description according to requirements"""
        if v is None:
            return ""
        if len(v) > 2000:
            raise ValueError("Task description must be at most 2000 characters long")
        return v.strip()

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        """Validate task status"""
        if v not in cls.ALLOWED_STATUSES:
            raise ValueError(f"Status must be one of: {cls.ALLOWED_STATUSES}")
        return v

    @field_validator("priority")
    @classmethod
    def validate_priority(cls, v: str) -> str:
        """Validate task priority"""
        if v not in cls.ALLOWED_PRIORITIES:
            raise ValueError(f"Priority must be one of: {cls.ALLOWED_PRIORITIES}")
        return v

    @field_validator("project_id")
    @classmethod
    def validate_project_id(cls, v: str) -> str:
        """Validate project ID is not empty"""
        if not v or len(v.strip()) == 0:
            raise ValueError("Project ID must be provided")
        return v.strip()

    @field_validator("reporter_id")
    @classmethod
    def validate_reporter_id(cls, v: str) -> str:
        """Validate reporter ID is not empty"""
        if not v or len(v.strip()) == 0:
            raise ValueError("Reporter ID must be provided")
        return v.strip()

    @field_validator("estimated_hours")
    @classmethod
    def validate_estimated_hours(cls, v: Optional[float]) -> Optional[float]:
        """Validate estimated hours is positive if provided"""
        if v is not None and v < 0:
            raise ValueError("Estimated hours must be positive")
        return v

    @field_validator("actual_hours")
    @classmethod
    def validate_actual_hours(cls, v: Optional[float]) -> Optional[float]:
        """Validate actual hours is positive if provided"""
        if v is not None and v < 0:
            raise ValueError("Actual hours must be positive")
        return v

    @model_validator(mode="after")
    def validate_business_logic(self) -> "Task":
        """Validate business logic rules"""
        # Validate due date format if provided
        if self.due_date:
            try:
                datetime.fromisoformat(self.due_date.replace("Z", "+00:00"))
            except ValueError:
                raise ValueError("Invalid due date format. Use ISO 8601 format")

        return self

    def update_timestamp(self) -> None:
        """Update the updated_at timestamp to current time"""
        self.updated_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    def assign_to_user(self, user_id: str) -> None:
        """Assign task to a user"""
        self.assignee_id = user_id
        self.update_timestamp()

    def unassign(self) -> None:
        """Remove task assignment"""
        self.assignee_id = None
        self.update_timestamp()

    def add_tag(self, tag: str) -> None:
        """Add a tag to the task"""
        if not self.tags:
            self.tags = []
        if tag not in self.tags:
            self.tags.append(tag)
            self.update_timestamp()

    def remove_tag(self, tag: str) -> None:
        """Remove a tag from the task"""
        if self.tags and tag in self.tags:
            self.tags.remove(tag)
            self.update_timestamp()

    def is_assigned(self) -> bool:
        """Check if task is assigned to someone"""
        return self.assignee_id is not None

    def is_completed(self) -> bool:
        """Check if task is completed"""
        return self.status == "DONE"

    def is_cancelled(self) -> bool:
        """Check if task is cancelled"""
        return self.status == "CANCELLED"

    def can_be_modified(self) -> bool:
        """Check if task can be modified (not done or cancelled)"""
        return self.status not in ["DONE", "CANCELLED"]

    def is_overdue(self) -> bool:
        """Check if task is overdue"""
        if not self.due_date or self.is_completed():
            return False
        
        try:
            due = datetime.fromisoformat(self.due_date.replace("Z", "+00:00"))
            now = datetime.now(timezone.utc)
            return now > due
        except ValueError:
            return False

    def to_api_response(self) -> Dict[str, Any]:
        """Convert to API response format"""
        data = self.model_dump(by_alias=True)
        # Add state for API compatibility
        data["state"] = self.state
        # Add computed fields
        data["isOverdue"] = self.is_overdue()
        data["isAssigned"] = self.is_assigned()
        return data

    model_config = ConfigDict(
        populate_by_name=True,
        use_enum_values=True,
        validate_assignment=True,
        extra="allow",
    )
