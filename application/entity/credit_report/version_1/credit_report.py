from datetime import datetime, timezone
from typing import Any, ClassVar, Dict, List, Optional

from pydantic import ConfigDict, Field

from common.entity.cyoda_entity import CyodaEntity


class CreditReport(CyodaEntity):
    ENTITY_NAME: ClassVar[str] = "CreditReport"
    ENTITY_VERSION: ClassVar[int] = 1

    applicant_id: str = Field(..., description="Reference to Applicant entity")

    credit_score: Optional[int] = Field(
        default=None,
        description="Credit score (300-850 range)",
    )

    bureau_name: str = Field(
        ..., description="Credit bureau name (EQUIFAX, EXPERIAN, TRANSUNION)"
    )
    report_date: str = Field(..., description="Date report was pulled (ISO 8601)")

    accounts_open: int = Field(default=0, description="Number of open accounts")
    accounts_closed: int = Field(default=0, description="Number of closed accounts")
    total_credit_limit: float = Field(default=0.0, description="Total available credit")
    total_credit_used: float = Field(default=0.0, description="Total credit used")
    credit_utilization_percent: float = Field(
        default=0.0, description="Credit utilization percentage"
    )

    delinquencies_30_days: int = Field(default=0, description="30-day delinquencies")
    delinquencies_60_days: int = Field(default=0, description="60-day delinquencies")
    delinquencies_90_days: int = Field(default=0, description="90-day delinquencies")

    public_records: int = Field(
        default=0, description="Number of public records (bankruptcies, liens)"
    )
    inquiries_last_6_months: int = Field(
        default=0, description="Hard inquiries in last 6 months"
    )

    average_account_age_months: int = Field(
        default=0, description="Average age of accounts in months"
    )
    oldest_account_months: int = Field(
        default=0, description="Age of oldest account in months"
    )

    risk_indicators: Optional[List[str]] = Field(
        default=None,
        description="List of risk indicators (RECENT_INQUIRY, HIGH_UTILIZATION, DELINQUENCY, etc.)",
    )

    created_at: Optional[str] = Field(
        default_factory=lambda: datetime.now(timezone.utc)
        .isoformat()
        .replace("+00:00", "Z"),
        alias="createdAt",
    )
    updated_at: Optional[str] = Field(default=None, alias="updatedAt")

    raw_report_data: Optional[Dict[str, Any]] = Field(
        default=None,
        alias="rawReportData",
        description="Raw data from credit bureau",
    )

    model_config = ConfigDict(populate_by_name=True)
