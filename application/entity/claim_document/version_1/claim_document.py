"""
ClaimDocument entity for document management in claims platform.

Represents documents uploaded with claims including images, PDFs, and reports.
"""

from datetime import datetime, timezone
from typing import Any, ClassVar, Dict, Optional

from pydantic import ConfigDict, Field, field_validator, model_validator

from common.entity.cyoda_entity import CyodaEntity


class ClaimDocument(CyodaEntity):
    """
    ClaimDocument represents a document associated with a claim.

    Supports images, PDFs, and other document types with metadata.
    """

    ENTITY_NAME: ClassVar[str] = "ClaimDocument"
    ENTITY_VERSION: ClassVar[int] = 1

    claim_id: str = Field(..., alias="claimId", description="Associated claim ID")
    document_type: str = Field(..., alias="documentType", description="Type of document")
    file_name: str = Field(..., alias="fileName", description="Name of the file")
    file_size_bytes: int = Field(
        ..., alias="fileSizeBytes", description="File size in bytes"
    )
    mime_type: str = Field(..., alias="mimeType", description="MIME type of document")
    storage_reference: str = Field(
        ..., alias="storageReference", description="Reference to stored file"
    )
    thumbnail_reference: Optional[str] = Field(
        default=None,
        alias="thumbnailReference",
        description="Reference to thumbnail if image",
    )
    uploaded_by_id: str = Field(
        ..., alias="uploadedById", description="User ID who uploaded"
    )
    upload_timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc)
        .isoformat()
        .replace("+00:00", "Z"),
        alias="uploadTimestamp",
        description="Upload timestamp",
    )
    document_date: Optional[str] = Field(
        default=None, alias="documentDate", description="Date of the document"
    )
    status: str = Field(default="VERIFIED", alias="status", description="Document status")
    created_at: Optional[str] = Field(
        default_factory=lambda: datetime.now(timezone.utc)
        .isoformat()
        .replace("+00:00", "Z"),
        alias="createdAt",
        description="Timestamp when the document was created (ISO 8601 format)",
    )
    updated_at: Optional[str] = Field(
        default=None,
        alias="updatedAt",
        description="Timestamp when the document was last updated (ISO 8601 format)",
    )

    @field_validator("document_type")
    @classmethod
    def validate_document_type(cls, v: str) -> str:
        allowed = ["IMAGE", "PDF", "REPORT", "POLICE_REPORT", "ESTIMATE", "OTHER"]
        if v not in allowed:
            raise ValueError(f"Document type must be one of {allowed}")
        return v

    @field_validator("file_size_bytes")
    @classmethod
    def validate_file_size(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("File size must be positive")
        if v > 100 * 1024 * 1024:  # 100MB limit
            raise ValueError("File size exceeds 100MB limit")
        return v

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        allowed = ["VERIFIED", "PENDING", "REJECTED"]
        if v not in allowed:
            raise ValueError(f"Status must be one of {allowed}")
        return v

    @model_validator(mode="after")
    def validate_business_logic(self) -> "ClaimDocument":
        """Validate business logic rules"""
        if self.file_size_bytes <= 0:
            raise ValueError("File size must be positive")
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

