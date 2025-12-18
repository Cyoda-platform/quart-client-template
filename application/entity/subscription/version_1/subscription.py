from datetime import datetime, timezone
from typing import Any, ClassVar, Dict, Optional

from pydantic import ConfigDict, Field, field_validator

from common.entity.cyoda_entity import CyodaEntity


class Subscription(CyodaEntity):
    ENTITY_NAME: ClassVar[str] = "Subscription"
    ENTITY_VERSION: ClassVar[int] = 1

    merchant_id: str = Field(..., description="Merchant identifier")
    customer_id: str = Field(..., description="Customer identifier")
    payment_method_token: str = Field(
        ..., description="Tokenized payment method for recurring charges"
    )

    plan_name: str = Field(..., description="Name of the subscription plan")
    amount: float = Field(..., gt=0, description="Recurring charge amount")
    currency: str = Field(..., description="ISO 4217 currency code")
    billing_interval: str = Field(
        default="monthly", description="Interval: daily, weekly, monthly, yearly"
    )

    trial_period_days: int = Field(default=0, ge=0, description="Trial period in days")
    trial_end_date: Optional[str] = Field(
        default=None, description="Trial end date (ISO 8601)"
    )

    next_billing_date: str = Field(
        ..., description="Next scheduled billing date (ISO 8601)"
    )
    last_billing_date: Optional[str] = Field(
        default=None, description="Last successful billing date"
    )

    retry_count: int = Field(default=0, ge=0, description="Failed billing retry count")
    max_retries: int = Field(default=3, ge=0, description="Max retry attempts")
    retry_backoff_days: int = Field(
        default=1, ge=1, description="Days between retry attempts"
    )

    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )
    created_at: Optional[str] = Field(
        default_factory=lambda: datetime.now(timezone.utc)
        .isoformat()
        .replace("+00:00", "Z"),
        description="Creation timestamp",
    )

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, v: str) -> str:
        if len(v) != 3 or not v.isupper():
            raise ValueError("Currency must be 3-letter ISO 4217 code")
        return v

    @field_validator("billing_interval")
    @classmethod
    def validate_billing_interval(cls, v: str) -> str:
        if v not in ["daily", "weekly", "monthly", "yearly"]:
            raise ValueError(
                "billing_interval must be daily, weekly, monthly, or yearly"
            )
        return v

    model_config = ConfigDict(
        populate_by_name=True,
        use_enum_values=True,
        validate_assignment=True,
        extra="allow",
    )
