from datetime import datetime, timezone
from typing import Any, ClassVar, Dict, List, Optional

from pydantic import ConfigDict, Field, field_validator, model_validator

from common.entity.cyoda_entity import CyodaEntity


class Compliance(CyodaEntity):
    """
    Compliance tracks regulatory compliance for trades and positions.

    Manages compliance checks and audit logging.
    States: initial_state -> created -> validated -> logged -> completed
    """

    ENTITY_NAME: ClassVar[str] = "Compliance"
    ENTITY_VERSION: ClassVar[int] = 1

    # Compliance identification
    compliance_id: str = Field(..., description="Unique compliance record identifier")
    entity_type: str = Field(..., description="ORDER, POSITION, PORTFOLIO")
    entity_id: str = Field(..., description="ID of the entity being tracked")
    account_id: str = Field(..., description="Trading account ID")

    # Compliance checks
    check_type: str = Field(
        ...,
        description="INSIDER_TRADING, MARKET_ABUSE, POSITION_LIMIT, SECTOR_RESTRICTION",
    )
    check_status: str = Field(
        default="PENDING", description="PENDING, PASSED, FAILED, WAIVED"
    )

    # Regulatory requirements
    regulation: str = Field(
        ..., description="Applicable regulation (e.g., MiFID II, Dodd-Frank)"
    )
    requirement: str = Field(..., description="Specific requirement being checked")

    # Check details
    check_result: Optional[Dict[str, Any]] = Field(
        None, description="Detailed check results"
    )
    is_compliant: bool = Field(default=False, description="Overall compliance status")

    # Audit trail
    checked_by: str = Field(..., description="User/system that performed check")
    approval_required: bool = Field(
        default=False, description="Requires manual approval"
    )
    approved_by: Optional[str] = Field(None, description="Approver if required")

    # Timestamps
    created_at: Optional[str] = Field(
        default_factory=lambda: datetime.now(timezone.utc)
        .isoformat()
        .replace("+00:00", "Z"),
        alias="createdAt",
    )
    checked_at: Optional[str] = Field(None, alias="checkedAt")
    approved_at: Optional[str] = Field(None, alias="approvedAt")
    logged_at: Optional[str] = Field(None, alias="loggedAt")

    # Notes
    notes: Optional[str] = Field(None, description="Compliance notes")

    ALLOWED_ENTITY_TYPES: ClassVar[List[str]] = ["ORDER", "POSITION", "PORTFOLIO"]
    ALLOWED_CHECK_TYPES: ClassVar[List[str]] = [
        "INSIDER_TRADING",
        "MARKET_ABUSE",
        "POSITION_LIMIT",
        "SECTOR_RESTRICTION",
    ]
    ALLOWED_CHECK_STATUS: ClassVar[List[str]] = [
        "PENDING",
        "PASSED",
        "FAILED",
        "WAIVED",
    ]

    @field_validator("entity_type")
    @classmethod
    def validate_entity_type(cls, v: str) -> str:
        if v not in cls.ALLOWED_ENTITY_TYPES:
            raise ValueError(f"Entity type must be one of: {cls.ALLOWED_ENTITY_TYPES}")
        return v

    @field_validator("check_type")
    @classmethod
    def validate_check_type(cls, v: str) -> str:
        if v not in cls.ALLOWED_CHECK_TYPES:
            raise ValueError(f"Check type must be one of: {cls.ALLOWED_CHECK_TYPES}")
        return v

    @field_validator("check_status")
    @classmethod
    def validate_check_status(cls, v: str) -> str:
        if v not in cls.ALLOWED_CHECK_STATUS:
            raise ValueError(f"Check status must be one of: {cls.ALLOWED_CHECK_STATUS}")
        return v

    @model_validator(mode="after")
    def validate_compliance_logic(self) -> "Compliance":
        if self.check_status == "PASSED":
            self.is_compliant = True
        elif self.check_status == "FAILED":
            self.is_compliant = False
        return self

    def mark_as_checked(self, is_compliant: bool, result: Dict[str, Any]) -> None:
        self.check_status = "PASSED" if is_compliant else "FAILED"
        self.is_compliant = is_compliant
        self.check_result = result
        self.checked_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    def approve(self, approver: str) -> None:
        self.approved_by = approver
        self.approved_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    def log_compliance(self) -> None:
        self.logged_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    model_config = ConfigDict(
        populate_by_name=True,
        use_enum_values=True,
        validate_assignment=True,
        extra="allow",
    )
