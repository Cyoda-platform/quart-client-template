"""
Compliance Entity for Real-Time Trading Platform

Represents regulatory compliance reports with audit trails and regulatory
reporting for trading compliance management.
"""

from datetime import datetime, timezone
from typing import Any, ClassVar, Dict, List, Optional

from pydantic import ConfigDict, Field, field_validator

from common.entity.cyoda_entity import CyodaEntity


class Compliance(CyodaEntity):
    """
    Compliance entity represents regulatory compliance reports and audit trails.

    Inherits from CyodaEntity to get common fields like entity_id, state, etc.
    The state field manages workflow states: initial_state -> validated -> submitted -> acknowledged
    """

    # Entity constants
    ENTITY_NAME: ClassVar[str] = "Compliance"
    ENTITY_VERSION: ClassVar[int] = 1

    # Required fields from functional requirements
    report_id: str = Field(
        ..., 
        alias="reportId",
        description="Business report identifier"
    )
    report_type: str = Field(
        ..., 
        alias="reportType",
        description="Report type: TRADE_REPORT, POSITION_REPORT, RISK_REPORT"
    )
    portfolio_id: str = Field(
        ..., 
        alias="portfolioId",
        description="Associated portfolio identifier"
    )
    reporting_date: str = Field(
        ..., 
        alias="reportingDate",
        description="Report date (ISO 8601 format)"
    )
    data: Dict[str, Any] = Field(
        ...,
        description="Report data content"
    )
    status: str = Field(
        default="PENDING",
        description="Report status: PENDING, SUBMITTED, ACKNOWLEDGED, REJECTED"
    )

    # Optional submission tracking
    submission_time: Optional[str] = Field(
        default=None,
        alias="submissionTime",
        description="Submission timestamp (ISO 8601 format)"
    )
    acknowledgment_time: Optional[str] = Field(
        default=None,
        alias="acknowledgmentTime",
        description="Acknowledgment timestamp (ISO 8601 format)"
    )

    # Regulatory metadata
    regulatory_authority: Optional[str] = Field(
        default=None,
        alias="regulatoryAuthority",
        description="Target regulatory authority"
    )
    regulation_reference: Optional[str] = Field(
        default=None,
        alias="regulationReference",
        description="Applicable regulation reference"
    )

    # Processing fields
    validation_data: Optional[Dict[str, Any]] = Field(
        default=None,
        alias="validationData",
        description="Compliance validation data"
    )
    submission_data: Optional[Dict[str, Any]] = Field(
        default=None,
        alias="submissionData",
        description="Submission processing data"
    )

    # Validation constants
    ALLOWED_REPORT_TYPES: ClassVar[List[str]] = [
        "TRADE_REPORT", "POSITION_REPORT", "RISK_REPORT"
    ]
    ALLOWED_STATUSES: ClassVar[List[str]] = [
        "PENDING", "SUBMITTED", "ACKNOWLEDGED", "REJECTED"
    ]

    @field_validator("report_id")
    @classmethod
    def validate_report_id(cls, v: str) -> str:
        """Validate report ID format"""
        if not v or len(v.strip()) == 0:
            raise ValueError("Report ID must be non-empty")
        if len(v) > 50:
            raise ValueError("Report ID must be at most 50 characters long")
        return v.strip()

    @field_validator("report_type")
    @classmethod
    def validate_report_type(cls, v: str) -> str:
        """Validate report type"""
        if v not in cls.ALLOWED_REPORT_TYPES:
            raise ValueError(f"Report type must be one of: {cls.ALLOWED_REPORT_TYPES}")
        return v

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        """Validate report status"""
        if v not in cls.ALLOWED_STATUSES:
            raise ValueError(f"Status must be one of: {cls.ALLOWED_STATUSES}")
        return v

    @field_validator("data")
    @classmethod
    def validate_data(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        """Validate report data is not empty"""
        if not v:
            raise ValueError("Report data cannot be empty")
        return v

    def is_submitted(self) -> bool:
        """Check if report has been submitted"""
        return self.status in ["SUBMITTED", "ACKNOWLEDGED"]

    def is_acknowledged(self) -> bool:
        """Check if report has been acknowledged"""
        return self.status == "ACKNOWLEDGED"

    def is_rejected(self) -> bool:
        """Check if report has been rejected"""
        return self.status == "REJECTED"

    def submit_report(self) -> None:
        """Mark report as submitted"""
        self.status = "SUBMITTED"
        self.submission_time = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        self.update_timestamp()

    def acknowledge_report(self) -> None:
        """Mark report as acknowledged"""
        self.status = "ACKNOWLEDGED"
        self.acknowledgment_time = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        self.update_timestamp()

    def reject_report(self) -> None:
        """Mark report as rejected"""
        self.status = "REJECTED"
        self.update_timestamp()

    def set_validation_data(self, validation_data: Dict[str, Any]) -> None:
        """Set validation data and update timestamp"""
        self.validation_data = validation_data
        self.update_timestamp()

    def set_submission_data(self, submission_data: Dict[str, Any]) -> None:
        """Set submission data and update timestamp"""
        self.submission_data = submission_data
        self.update_timestamp()

    def update_timestamp(self) -> None:
        """Update the updated_at timestamp to current time"""
        self.updated_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    def to_api_response(self) -> Dict[str, Any]:
        """Convert to API response format"""
        data = self.model_dump(by_alias=True)
        # Add state for API compatibility
        data["state"] = self.state
        return data

    model_config = ConfigDict(
        populate_by_name=True,
        use_enum_values=True,
        validate_assignment=True,
        extra="allow",
    )
