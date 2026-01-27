"""
DataAnalysis entity for CSV analysis and reporting.

Represents a CSV analysis job that downloads, processes, and analyzes data.
"""

from datetime import datetime, timezone
from typing import Any, ClassVar, Dict, List, Optional

from pydantic import Field, field_validator

from common.entity.cyoda_entity import CyodaEntity


class DataAnalysis(CyodaEntity):
    """
    DataAnalysis represents a CSV analysis job.

    States: initial_state -> created -> validated -> analyzed -> completed
    """

    ENTITY_NAME: ClassVar[str] = "DataAnalysis"
    ENTITY_VERSION: ClassVar[int] = 1

    csv_url: str = Field(..., description="URL to the CSV file")
    file_name: Optional[str] = Field(
        default=None,
        alias="fileName",
        description="Name of the downloaded file",
    )
    row_count: Optional[int] = Field(
        default=None,
        alias="rowCount",
        description="Number of rows in the CSV",
    )
    column_count: Optional[int] = Field(
        default=None,
        alias="columnCount",
        description="Number of columns",
    )
    columns: Optional[List[str]] = Field(
        default=None,
        description="List of column names",
    )
    summary_stats: Optional[Dict[str, Any]] = Field(
        default=None,
        alias="summaryStats",
        description="Summary statistics (mean, median, std, etc.)",
    )
    analysis_result: Optional[Dict[str, Any]] = Field(
        default=None,
        alias="analysisResult",
        description="Full analysis result as JSON",
    )
    status: Optional[str] = Field(
        default="pending",
        description="Current processing status",
    )
    created_at: Optional[str] = Field(
        default_factory=lambda: datetime.now(timezone.utc)
        .isoformat()
        .replace("+00:00", "Z"),
        alias="createdAt",
        description="Timestamp when created",
    )
    updated_at: Optional[str] = Field(
        default=None,
        alias="updatedAt",
        description="Timestamp when last updated",
    )

    @field_validator("csv_url")
    @classmethod
    def validate_csv_url(cls, v: str) -> str:
        """Validate CSV URL format"""
        if not v or len(v.strip()) == 0:
            raise ValueError("CSV URL is required")
        if not v.startswith(("http://", "https://")):
            raise ValueError("CSV URL must start with http:// or https://")
        return v

    def update_timestamp(self) -> None:
        """Update the updated_at timestamp to current time"""
        self.updated_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

