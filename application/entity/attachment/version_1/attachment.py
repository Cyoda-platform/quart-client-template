"""
Attachment Entity for Project Management Application

File attachments associated with tasks supporting various file types
with size limits and access control.
"""

from datetime import datetime, timezone
from typing import Any, ClassVar, Dict, List, Optional

from pydantic import ConfigDict, Field, field_validator, model_validator

from common.entity.cyoda_entity import CyodaEntity


class Attachment(CyodaEntity):
    """
    Attachment entity represents file attachments associated with tasks.
    
    Supports various file types with size limits and access control.
    State managed by workflow: initial_state -> uploaded -> (optional: deleted).
    """

    # Entity constants
    ENTITY_NAME: ClassVar[str] = "Attachment"
    ENTITY_VERSION: ClassVar[int] = 1

    # Core attachment fields
    attachment_id: str = Field(..., description="Business identifier for the attachment")
    task_id: str = Field(..., description="Technical ID of the parent task")
    filename: str = Field(..., description="Original filename")
    url: str = Field(..., description="Storage URL for the file")
    uploaded_by: str = Field(..., description="Technical ID of the uploader")
    file_size: Optional[int] = Field(
        default=None,
        alias="fileSize",
        description="File size in bytes"
    )
    content_type: Optional[str] = Field(
        default=None,
        alias="contentType",
        description="MIME type of the file"
    )

    # Timestamps
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc)
        .isoformat()
        .replace("+00:00", "Z"),
        alias="createdAt",
        description="Timestamp when the attachment was uploaded (ISO 8601 format)",
    )
    updated_at: Optional[str] = Field(
        default=None,
        alias="updatedAt",
        description="Timestamp when the attachment was last updated (ISO 8601 format)",
    )

    # Constants
    MAX_FILE_SIZE: ClassVar[int] = 10 * 1024 * 1024  # 10MB
    ALLOWED_CONTENT_TYPES: ClassVar[List[str]] = [
        "application/pdf",
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.ms-excel",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "text/plain",
        "text/csv",
        "image/jpeg",
        "image/png",
        "image/gif",
        "application/zip",
        "application/x-zip-compressed",
    ]

    @field_validator("attachment_id")
    @classmethod
    def validate_attachment_id(cls, v: str) -> str:
        """Validate attachment_id field"""
        if not v or len(v.strip()) == 0:
            raise ValueError("Attachment ID must be non-empty")
        if len(v) < 3:
            raise ValueError("Attachment ID must be at least 3 characters long")
        if len(v) > 50:
            raise ValueError("Attachment ID must be at most 50 characters long")
        return v.strip()

    @field_validator("task_id")
    @classmethod
    def validate_task_id(cls, v: str) -> str:
        """Validate task_id field"""
        if not v or len(v.strip()) == 0:
            raise ValueError("Task ID must be non-empty")
        return v.strip()

    @field_validator("filename")
    @classmethod
    def validate_filename(cls, v: str) -> str:
        """Validate filename field"""
        if not v or len(v.strip()) == 0:
            raise ValueError("Filename must be non-empty")
        if len(v) > 255:
            raise ValueError("Filename must be at most 255 characters long")
        
        # Basic filename validation
        filename = v.strip()
        if not filename or filename in [".", ".."]:
            raise ValueError("Invalid filename")
        
        # Check for dangerous characters
        dangerous_chars = ["<", ">", ":", '"', "|", "?", "*", "\0"]
        if any(char in filename for char in dangerous_chars):
            raise ValueError("Filename contains invalid characters")
        
        return filename

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        """Validate url field"""
        if not v or len(v.strip()) == 0:
            raise ValueError("URL must be non-empty")
        if len(v) > 500:
            raise ValueError("URL must be at most 500 characters long")
        return v.strip()

    @field_validator("uploaded_by")
    @classmethod
    def validate_uploaded_by(cls, v: str) -> str:
        """Validate uploaded_by field"""
        if not v or len(v.strip()) == 0:
            raise ValueError("Uploaded by must be non-empty")
        return v.strip()

    @field_validator("file_size")
    @classmethod
    def validate_file_size(cls, v: Optional[int]) -> Optional[int]:
        """Validate file_size field"""
        if v is None:
            return None
        if v < 0:
            raise ValueError("File size must be non-negative")
        if v > cls.MAX_FILE_SIZE:
            raise ValueError(f"File size must be less than {cls.MAX_FILE_SIZE} bytes (10MB)")
        return v

    @field_validator("content_type")
    @classmethod
    def validate_content_type(cls, v: Optional[str]) -> Optional[str]:
        """Validate content_type field"""
        if v is None:
            return None
        
        content_type = v.strip().lower()
        if not content_type:
            return None
        
        # Allow any content type for now, but log if not in allowed list
        # In production, you might want to enforce the allowed list
        return content_type

    @model_validator(mode="after")
    def validate_business_logic(self) -> "Attachment":
        """Validate business logic rules"""
        # Additional business rules can be added here
        return self

    def update_timestamp(self) -> None:
        """Update the updated_at timestamp to current time"""
        self.updated_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    def is_image(self) -> bool:
        """Check if attachment is an image"""
        if not self.content_type:
            return False
        return self.content_type.startswith("image/")

    def is_document(self) -> bool:
        """Check if attachment is a document"""
        if not self.content_type:
            return False
        document_types = [
            "application/pdf",
            "application/msword",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "text/plain",
        ]
        return self.content_type in document_types

    def get_file_extension(self) -> str:
        """Get file extension from filename"""
        if "." in self.filename:
            return self.filename.split(".")[-1].lower()
        return ""

    def to_api_response(self) -> Dict[str, Any]:
        """Convert to API response format"""
        data = self.model_dump(by_alias=True)
        data["state"] = self.state
        data["isImage"] = self.is_image()
        data["isDocument"] = self.is_document()
        data["fileExtension"] = self.get_file_extension()
        return data

    model_config = ConfigDict(
        populate_by_name=True,
        use_enum_values=True,
        validate_assignment=True,
        extra="allow",
    )
