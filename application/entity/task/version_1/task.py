"""
Task Entity for Project Management Application

Core entity representing work items within projects with workflow states:
backlog -> todo -> in_progress -> review -> done
"""

from datetime import datetime, timezone
from typing import Any, ClassVar, Dict, List, Optional

from pydantic import ConfigDict, Field, field_validator, model_validator

from common.entity.cyoda_entity import CyodaEntity


class Task(CyodaEntity):
    """
    Task entity represents work items within projects.
    
    Core entity with workflow states: backlog -> todo -> in_progress -> review -> done
    Supports assignments, priorities, time tracking, and dependencies.
    """

    # Entity constants
    ENTITY_NAME: ClassVar[str] = "Task"
    ENTITY_VERSION: ClassVar[int] = 1

    # Core task fields
    task_id: str = Field(..., description="Business identifier for the task")
    project_id: str = Field(..., description="Technical ID of the parent project")
    title: str = Field(..., description="Task title")
    description: str = Field(..., description="Task description")
    assignee_id: Optional[str] = Field(
        default=None,
        alias="assigneeId",
        description="Technical ID of assigned user"
    )
    priority: str = Field(..., description="Task priority: HIGH, MEDIUM, LOW")
    estimate_hours: Optional[float] = Field(
        default=None,
        alias="estimateHours",
        description="Estimated hours to complete"
    )
    logged_hours: Optional[float] = Field(
        default=0.0,
        alias="loggedHours",
        description="Actual hours logged"
    )
    due_date: Optional[str] = Field(
        default=None,
        alias="dueDate",
        description="Task due date (ISO 8601 format)"
    )
    dependencies: Optional[List[str]] = Field(
        default_factory=list,
        description="List of task technical IDs this task depends on"
    )

    # Timestamps
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

    # Constants
    ALLOWED_PRIORITIES: ClassVar[List[str]] = ["HIGH", "MEDIUM", "LOW"]

    @field_validator("task_id")
    @classmethod
    def validate_task_id(cls, v: str) -> str:
        """Validate task_id field"""
        if not v or len(v.strip()) == 0:
            raise ValueError("Task ID must be non-empty")
        if len(v) < 3:
            raise ValueError("Task ID must be at least 3 characters long")
        if len(v) > 50:
            raise ValueError("Task ID must be at most 50 characters long")
        return v.strip()

    @field_validator("project_id")
    @classmethod
    def validate_project_id(cls, v: str) -> str:
        """Validate project_id field"""
        if not v or len(v.strip()) == 0:
            raise ValueError("Project ID must be non-empty")
        return v.strip()

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str) -> str:
        """Validate title field"""
        if not v or len(v.strip()) == 0:
            raise ValueError("Task title must be non-empty")
        if len(v) < 3:
            raise ValueError("Task title must be at least 3 characters long")
        if len(v) > 200:
            raise ValueError("Task title must be at most 200 characters long")
        return v.strip()

    @field_validator("description")
    @classmethod
    def validate_description(cls, v: str) -> str:
        """Validate description field"""
        if not v or len(v.strip()) == 0:
            raise ValueError("Task description must be non-empty")
        if len(v) > 2000:
            raise ValueError("Task description must be at most 2000 characters long")
        return v.strip()

    @field_validator("priority")
    @classmethod
    def validate_priority(cls, v: str) -> str:
        """Validate priority field"""
        if v not in cls.ALLOWED_PRIORITIES:
            raise ValueError(f"Priority must be one of: {cls.ALLOWED_PRIORITIES}")
        return v

    @field_validator("estimate_hours")
    @classmethod
    def validate_estimate_hours(cls, v: Optional[float]) -> Optional[float]:
        """Validate estimate_hours field"""
        if v is None:
            return None
        if v < 0:
            raise ValueError("Estimate hours must be non-negative")
        if v > 1000:  # Reasonable upper limit
            raise ValueError("Estimate hours must be less than 1000")
        return v

    @field_validator("logged_hours")
    @classmethod
    def validate_logged_hours(cls, v: Optional[float]) -> float:
        """Validate logged_hours field"""
        if v is None:
            return 0.0
        if v < 0:
            raise ValueError("Logged hours must be non-negative")
        if v > 2000:  # Reasonable upper limit
            raise ValueError("Logged hours must be less than 2000")
        return v

    @field_validator("due_date")
    @classmethod
    def validate_due_date(cls, v: Optional[str]) -> Optional[str]:
        """Validate due_date field"""
        if v is None:
            return None
        
        if not v.strip():
            return None
            
        # Basic ISO 8601 format validation
        try:
            datetime.fromisoformat(v.replace('Z', '+00:00'))
        except ValueError:
            raise ValueError("Due date must be in ISO 8601 format")
        
        return v.strip()

    @field_validator("dependencies")
    @classmethod
    def validate_dependencies(cls, v: Optional[List[str]]) -> List[str]:
        """Validate dependencies field"""
        if v is None:
            return []
        
        # Remove duplicates and empty strings
        cleaned_deps = []
        for dep_id in v:
            if dep_id and dep_id.strip():
                dep_id = dep_id.strip()
                if dep_id not in cleaned_deps:
                    cleaned_deps.append(dep_id)
        
        return cleaned_deps

    @model_validator(mode="after")
    def validate_business_logic(self) -> "Task":
        """Validate business logic rules"""
        # Validate logged hours vs estimate
        if (self.estimate_hours is not None and 
            self.logged_hours is not None and 
            self.logged_hours > self.estimate_hours * 1.5):
            raise ValueError("Logged hours cannot exceed 150% of estimated hours")
        
        return self

    def update_timestamp(self) -> None:
        """Update the updated_at timestamp to current time"""
        self.updated_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    def add_logged_hours(self, hours: float) -> None:
        """Add hours to logged time"""
        if hours > 0:
            self.logged_hours = (self.logged_hours or 0.0) + hours
            self.update_timestamp()

    def is_overdue(self) -> bool:
        """Check if task is overdue"""
        if not self.due_date:
            return False
        
        try:
            due_dt = datetime.fromisoformat(self.due_date.replace('Z', '+00:00'))
            return datetime.now(timezone.utc) > due_dt
        except ValueError:
            return False

    def is_high_priority(self) -> bool:
        """Check if task has high priority"""
        return self.priority == "HIGH"

    def has_dependencies(self) -> bool:
        """Check if task has dependencies"""
        return len(self.dependencies) > 0

    def to_api_response(self) -> Dict[str, Any]:
        """Convert to API response format"""
        data = self.model_dump(by_alias=True)
        data["state"] = self.state
        data["isOverdue"] = self.is_overdue()
        return data

    model_config = ConfigDict(
        populate_by_name=True,
        use_enum_values=True,
        validate_assignment=True,
        extra="allow",
    )
