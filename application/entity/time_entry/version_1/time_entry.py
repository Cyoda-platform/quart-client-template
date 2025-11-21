"""
TimeEntry Entity for Project Management Application

Time tracking for tasks with automatic duration calculation and validation.
Supports both manual time entry and timer-based tracking.
"""

from datetime import datetime, timezone
from typing import Any, ClassVar, Dict, Optional

from pydantic import ConfigDict, Field, field_validator, model_validator

from common.entity.cyoda_entity import CyodaEntity


class TimeEntry(CyodaEntity):
    """
    TimeEntry entity represents time tracking for tasks.

    Supports both manual time entry and timer-based tracking with automatic
    duration calculation. State managed by workflow:
    initial_state -> logged -> (optional: approved/rejected).
    """

    # Entity constants
    ENTITY_NAME: ClassVar[str] = "TimeEntry"
    ENTITY_VERSION: ClassVar[int] = 1

    # Core time entry fields
    entry_id: str = Field(..., description="Business identifier for the time entry")
    task_id: str = Field(..., description="Technical ID of the parent task")
    user_id: str = Field(..., description="Technical ID of the user logging time")
    start_time: str = Field(..., description="Start timestamp (ISO 8601 format)")
    end_time: Optional[str] = Field(
        default=None, alias="endTime", description="End timestamp (ISO 8601 format)"
    )
    duration_minutes: int = Field(..., description="Duration in minutes")
    description: Optional[str] = Field(
        default=None, description="Description of work performed"
    )

    # Timestamps
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc)
        .isoformat()
        .replace("+00:00", "Z"),
        alias="createdAt",
        description="Timestamp when the time entry was created (ISO 8601 format)",
    )
    updated_at: Optional[str] = Field(
        default=None,
        alias="updatedAt",
        description="Timestamp when the time entry was last updated (ISO 8601 format)",
    )

    # Constants
    MAX_DURATION_MINUTES: ClassVar[int] = 24 * 60  # 24 hours

    @field_validator("entry_id")
    @classmethod
    def validate_entry_id(cls, v: str) -> str:
        """Validate entry_id field"""
        if not v or len(v.strip()) == 0:
            raise ValueError("Entry ID must be non-empty")
        if len(v) < 3:
            raise ValueError("Entry ID must be at least 3 characters long")
        if len(v) > 50:
            raise ValueError("Entry ID must be at most 50 characters long")
        return v.strip()

    @field_validator("task_id")
    @classmethod
    def validate_task_id(cls, v: str) -> str:
        """Validate task_id field"""
        if not v or len(v.strip()) == 0:
            raise ValueError("Task ID must be non-empty")
        return v.strip()

    @field_validator("user_id")
    @classmethod
    def validate_user_id(cls, v: str) -> str:
        """Validate user_id field"""
        if not v or len(v.strip()) == 0:
            raise ValueError("User ID must be non-empty")
        return v.strip()

    @field_validator("start_time")
    @classmethod
    def validate_start_time(cls, v: str) -> str:
        """Validate start_time field"""
        if not v or len(v.strip()) == 0:
            raise ValueError("Start time must be non-empty")

        # Basic ISO 8601 format validation
        try:
            start_dt = datetime.fromisoformat(v.replace("Z", "+00:00"))
            # Check if start time is not in the future
            if start_dt > datetime.now(timezone.utc):
                raise ValueError("Start time cannot be in the future")
        except ValueError as e:
            if "Start time cannot be in the future" in str(e):
                raise e
            raise ValueError("Start time must be in ISO 8601 format")

        return v.strip()

    @field_validator("end_time")
    @classmethod
    def validate_end_time(cls, v: Optional[str]) -> Optional[str]:
        """Validate end_time field"""
        if v is None:
            return None

        if not v.strip():
            return None

        # Basic ISO 8601 format validation
        try:
            datetime.fromisoformat(v.replace("Z", "+00:00"))
        except ValueError:
            raise ValueError("End time must be in ISO 8601 format")

        return v.strip()

    @field_validator("duration_minutes")
    @classmethod
    def validate_duration_minutes(cls, v: int) -> int:
        """Validate duration_minutes field"""
        if v <= 0:
            raise ValueError("Duration must be positive")
        if v > cls.MAX_DURATION_MINUTES:
            raise ValueError(
                f"Duration must be less than {cls.MAX_DURATION_MINUTES} minutes (24 hours)"
            )
        return v

    @field_validator("description")
    @classmethod
    def validate_description(cls, v: Optional[str]) -> Optional[str]:
        """Validate description field"""
        if v is None:
            return None

        if not v.strip():
            return None

        if len(v) > 500:
            raise ValueError("Description must be at most 500 characters long")

        return v.strip()

    @model_validator(mode="after")
    def validate_business_logic(self) -> "TimeEntry":
        """Validate business logic rules"""
        # Validate end time is after start time if both are provided
        if self.start_time and self.end_time:
            try:
                start_dt = datetime.fromisoformat(
                    self.start_time.replace("Z", "+00:00")
                )
                end_dt = datetime.fromisoformat(self.end_time.replace("Z", "+00:00"))

                if end_dt <= start_dt:
                    raise ValueError("End time must be after start time")

                # Calculate expected duration and validate against provided duration
                expected_duration = int((end_dt - start_dt).total_seconds() / 60)
                if (
                    abs(expected_duration - self.duration_minutes) > 1
                ):  # Allow 1 minute tolerance
                    raise ValueError("Duration does not match start and end times")

            except ValueError as e:
                if any(
                    msg in str(e)
                    for msg in [
                        "End time must be after start time",
                        "Duration does not match",
                    ]
                ):
                    raise e
                # If date parsing fails, let the field validators handle it

        return self

    def update_timestamp(self) -> None:
        """Update the updated_at timestamp to current time"""
        self.updated_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    def get_duration_hours(self) -> float:
        """Get duration in hours"""
        return self.duration_minutes / 60.0

    def is_long_session(self) -> bool:
        """Check if this is a long work session (>4 hours)"""
        return self.duration_minutes > 240

    def calculate_duration_from_times(self) -> Optional[int]:
        """Calculate duration in minutes from start and end times"""
        if not self.start_time or not self.end_time:
            return None

        try:
            start_dt = datetime.fromisoformat(self.start_time.replace("Z", "+00:00"))
            end_dt = datetime.fromisoformat(self.end_time.replace("Z", "+00:00"))
            return int((end_dt - start_dt).total_seconds() / 60)
        except ValueError:
            return None

    def to_api_response(self) -> Dict[str, Any]:
        """Convert to API response format"""
        data = self.model_dump(by_alias=True)
        data["state"] = self.state
        data["durationHours"] = self.get_duration_hours()
        data["isLongSession"] = self.is_long_session()
        return data

    model_config = ConfigDict(
        populate_by_name=True,
        use_enum_values=True,
        validate_assignment=True,
        extra="allow",
    )
