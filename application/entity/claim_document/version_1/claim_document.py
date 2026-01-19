"""
ClaimDocument entity for document management in claims platform.

Represents documents uploaded with claims including images, PDFs, and reports.
"""

from datetime import datetime, timezone
from typing import ClassVar, Optional

from pydantic import Field, field_validator

from common.entity.cyoda_entity import CyodaEntity


class ClaimDocument(CyodaEntity):
    """
    ClaimDocument represents a document associated with a claim.
    
    Supports images, PDFs, and other document types with metadata.
    """

    ENTITY_NAME: ClassVar[str] = "ClaimDocument"
    ENTITY_VERSION: ClassVar[int] = 1

    claim_id: str = Field(..., description="Associated claim ID")
    document_name: str = Field(..., description="Name of the document")
    document_type: str = Field(..., description="Type (IMAGE, PDF, REPORT, etc.)")
    file_path: str = Field(..., description="Path to stored file")
    file_size: int = Field(..., description="File size in bytes")
    mime_type: str = Field(..., description="MIME type of document")
    uploaded_by: str = Field(..., description="User ID who uploaded")
    uploaded_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc)
        .isoformat()
        .replace("+00:00", "Z"),
        description="Upload timestamp",
    )
    thumbnail_path: Optional[str] = Field(
        default=None, description="Path to thumbnail if image"
    )
    is_verified: bool = Field(
        default=False, description="Whether document is verified"
    )

    @field_validator("document_type")
    @classmethod
    def validate_document_type(cls, v: str) -> str:
        allowed = ["IMAGE", "PDF", "REPORT", "POLICE_REPORT", "ESTIMATE", "OTHER"]
        if v not in allowed:
            raise ValueError(f"Document type must be one of {allowed}")
        return v

    @field_validator("file_size")
    @classmethod
    def validate_file_size(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("File size must be positive")
        if v > 100 * 1024 * 1024:  # 100MB limit
            raise ValueError("File size exceeds 100MB limit")
        return v

