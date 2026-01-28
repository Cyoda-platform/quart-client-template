"""
ActivityReport entity for Activity Tracker application.

Represents a daily activity report that aggregates user activity data,
detects anomalies, and tracks the reporting workflow.
"""

from datetime import datetime, timezone
from typing import Any, ClassVar, Dict, List, Optional

from pydantic import ConfigDict, Field

from common.entity.cyoda_entity import CyodaEntity


class ActivityReport(CyodaEntity):
    """
    ActivityReport represents a daily activity summary report.

    Inherits from CyodaEntity to get common fields like entity_id, state, etc.
    The state field manages workflow states:
    initial_state -> ingested -> processed -> reported -> completed
    """

    ENTITY_NAME: ClassVar[str] = "ActivityReport"
    ENTITY_VERSION: ClassVar[int] = 1

    report_date: str = Field(..., description="Date of the report (YYYY-MM-DD)")
    total_activities: int = Field(
        default=0, description="Total number of activities for the day"
    )
    top_activity_types: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Top 5 activity types with counts",
    )
    trend_highlights: List[str] = Field(
        default_factory=list,
        description="Brief trend highlights (e.g., +/−% change vs 7-day average)",
    )
    flagged_anomalies: List[Dict[str, Any]] = Field(
        default_factory=list,
        description=(
            "List of flagged anomalies (user IDs or activity types "
            "with z-score > 3)"
        ),
    )
    raw_data_location: Optional[str] = Field(
        default=None,
        description="Path or reference to raw fetched data for traceability",
    )
    processing_metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Metadata about processing (timestamps, error counts, etc.)",
    )
    report_content_html: Optional[str] = Field(
        default=None,
        description="HTML formatted report content for email",
    )
    report_content_text: Optional[str] = Field(
        default=None,
        description="Plain text formatted report content for email fallback",
    )
    email_sent_at: Optional[str] = Field(
        default=None,
        description="Timestamp when report was emailed",
    )
    email_recipient: Optional[str] = Field(
        default=None,
        description="Email address where report was sent",
    )

    created_at: Optional[str] = Field(
        default_factory=lambda: datetime.now(timezone.utc)
        .isoformat()
        .replace("+00:00", "Z"),
        alias="createdAt",
        description="Timestamp when the report was created",
    )
    updated_at: Optional[str] = Field(
        default=None,
        alias="updatedAt",
        description="Timestamp when the report was last updated",
    )

    model_config = ConfigDict(
        extra="allow",
        use_enum_values=True,
        validate_assignment=True,
        populate_by_name=True,
    )
