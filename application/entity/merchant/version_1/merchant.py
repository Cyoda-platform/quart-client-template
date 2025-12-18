from datetime import datetime, timezone
from typing import Any, ClassVar, Dict, List, Optional

from pydantic import ConfigDict, Field, field_validator

from common.entity.cyoda_entity import CyodaEntity


class Merchant(CyodaEntity):
    ENTITY_NAME: ClassVar[str] = "Merchant"
    ENTITY_VERSION: ClassVar[int] = 1

    merchant_name: str = Field(..., description="Legal merchant name")
    merchant_email: str = Field(..., description="Merchant contact email")
    settlement_currency: str = Field(
        ..., description="Default settlement currency (ISO 4217)"
    )

    kyc_status: str = Field(
        default="pending", description="KYC status: pending, verified, rejected"
    )
    kyc_fields: Dict[str, Any] = Field(
        default_factory=dict, description="KYC verification data"
    )

    fraud_threshold: float = Field(
        default=75.0, ge=0.0, le=100.0, description="Fraud score threshold for decline"
    )
    fraud_review_threshold: float = Field(
        default=50.0, ge=0.0, le=100.0, description="Fraud score threshold for review"
    )

    supported_currencies: List[str] = Field(
        default_factory=lambda: ["USD", "EUR", "GBP"],
        description="List of supported currencies",
    )

    max_transaction_amount: float = Field(
        default=10000.0, gt=0, description="Maximum transaction amount"
    )
    daily_volume_limit: float = Field(
        default=100000.0, gt=0, description="Daily transaction volume limit"
    )

    webhook_url: Optional[str] = Field(
        default=None, description="Webhook URL for payment events"
    )
    webhook_secret: Optional[str] = Field(
        default=None, description="Webhook signing secret"
    )

    is_active: bool = Field(default=True, description="Merchant active status")
    created_at: Optional[str] = Field(
        default_factory=lambda: datetime.now(timezone.utc)
        .isoformat()
        .replace("+00:00", "Z"),
        description="Creation timestamp",
    )

    @field_validator("settlement_currency")
    @classmethod
    def validate_currency(cls, v: str) -> str:
        if len(v) != 3 or not v.isupper():
            raise ValueError("Currency must be 3-letter ISO 4217 code")
        return v

    @field_validator("kyc_status")
    @classmethod
    def validate_kyc_status(cls, v: str) -> str:
        if v not in ["pending", "verified", "rejected"]:
            raise ValueError("kyc_status must be pending, verified, or rejected")
        return v

    @field_validator("supported_currencies")
    @classmethod
    def validate_supported_currencies(cls, v: List[str]) -> List[str]:
        for currency in v:
            if len(currency) != 3 or not currency.isupper():
                raise ValueError("Each currency must be 3-letter ISO 4217 code")
        return v

    model_config = ConfigDict(
        populate_by_name=True,
        use_enum_values=True,
        validate_assignment=True,
        extra="allow",
    )

