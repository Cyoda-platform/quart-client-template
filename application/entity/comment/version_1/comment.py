"""
Comment Entity for Project Management Application

Enables collaboration through task comments with mentions and notifications.
Comments support real-time collaboration features.
"""

from datetime import datetime, timezone
from typing import Any, ClassVar, Dict, List, Optional

from pydantic import ConfigDict, Field, field_validator, model_validator

from common.entity.cyoda_entity import CyodaEntity


class Comment(CyodaEntity):
    """
    Comment entity enables collaboration through task comments.
    
    Supports mentions, notifications, and real-time collaboration features.
    State managed by workflow: initial_state -> posted -> (optional: edited).
    """

    # Entity constants
    ENTITY_NAME: ClassVar[str] = "Comment"
    ENTITY_VERSION: ClassVar[int] = 1

    # Core comment fields
    comment_id: str = Field(..., description="Business identifier for the comment")
    task_id: str = Field(..., description="Technical ID of the parent task")
    author_id: str = Field(..., description="Technical ID of the comment author")
    content: str = Field(..., description="Comment content")
    mentions: Optional[List[str]] = Field(
        default_factory=list,
        description="List of mentioned user technical IDs"
    )

    # Timestamps
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc)
        .isoformat()
        .replace("+00:00", "Z"),
        alias="createdAt",
        description="Comment creation timestamp (ISO 8601 format)",
    )
    updated_at: Optional[str] = Field(
        default=None,
        alias="updatedAt",
        description="Timestamp when the comment was last updated (ISO 8601 format)",
    )

    @field_validator("comment_id")
    @classmethod
    def validate_comment_id(cls, v: str) -> str:
        """Validate comment_id field"""
        if not v or len(v.strip()) == 0:
            raise ValueError("Comment ID must be non-empty")
        if len(v) < 3:
            raise ValueError("Comment ID must be at least 3 characters long")
        if len(v) > 50:
            raise ValueError("Comment ID must be at most 50 characters long")
        return v.strip()

    @field_validator("task_id")
    @classmethod
    def validate_task_id(cls, v: str) -> str:
        """Validate task_id field"""
        if not v or len(v.strip()) == 0:
            raise ValueError("Task ID must be non-empty")
        return v.strip()

    @field_validator("author_id")
    @classmethod
    def validate_author_id(cls, v: str) -> str:
        """Validate author_id field"""
        if not v or len(v.strip()) == 0:
            raise ValueError("Author ID must be non-empty")
        return v.strip()

    @field_validator("content")
    @classmethod
    def validate_content(cls, v: str) -> str:
        """Validate content field"""
        if not v or len(v.strip()) == 0:
            raise ValueError("Comment content must be non-empty")
        if len(v) > 1000:
            raise ValueError("Comment content must be at most 1000 characters long")
        return v.strip()

    @field_validator("mentions")
    @classmethod
    def validate_mentions(cls, v: Optional[List[str]]) -> List[str]:
        """Validate mentions field"""
        if v is None:
            return []
        
        # Remove duplicates and empty strings
        cleaned_mentions = []
        for user_id in v:
            if user_id and user_id.strip():
                user_id = user_id.strip()
                if user_id not in cleaned_mentions:
                    cleaned_mentions.append(user_id)
        
        return cleaned_mentions

    @model_validator(mode="after")
    def validate_business_logic(self) -> "Comment":
        """Validate business logic rules"""
        # Additional business rules can be added here
        return self

    def update_timestamp(self) -> None:
        """Update the updated_at timestamp to current time"""
        self.updated_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    def add_mention(self, user_id: str) -> None:
        """Add a user mention to the comment"""
        if user_id and user_id not in (self.mentions or []):
            if self.mentions is None:
                self.mentions = []
            self.mentions.append(user_id)
            self.update_timestamp()

    def has_mentions(self) -> bool:
        """Check if comment has mentions"""
        return len(self.mentions or []) > 0

    def is_edited(self) -> bool:
        """Check if comment has been edited"""
        return self.updated_at is not None

    def to_api_response(self) -> Dict[str, Any]:
        """Convert to API response format"""
        data = self.model_dump(by_alias=True)
        data["state"] = self.state
        data["isEdited"] = self.is_edited()
        return data

    model_config = ConfigDict(
        populate_by_name=True,
        use_enum_values=True,
        validate_assignment=True,
        extra="allow",
    )
