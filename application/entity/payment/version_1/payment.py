from datetime import datetime, timezone
from typing import Any, ClassVar, Dict, List, Optional

from pydantic import ConfigDict, Field, field_validator

from common.entity.cyoda_entity import CyodaEntity


class Payment(CyodaEntity):
    ENTITY_NAME: ClassVar[str] = "Payment"
    ENTITY_VERSION: ClassVar[int] = 1

    merchant_id: str = Field(..., description="Merchant identifier")
    customer_id: str = Field(..., description="Customer identifier")
    amount: float = Field(..., gt=0, description="Payment amount in original currency")
    currency: str = Field(..., description="ISO 4217 currency code (e.g., EUR, USD)")
    settlement_currency: str = Field(
        ..., description="Settlement currency for merchant"
    )
    exchange_rate: float = Field(default=1.0, ge=0, description="Exchange rate applied")
    settlement_amount: float = Field(
        default=0.0, ge=0, description="Amount in settlement currency"
    )

    payment_method_token: str = Field(
        ..., description="Tokenized payment method (no raw PAN)"
    )
    payment_method_type: str = Field(
        default="card", description="Type: card, bank_transfer, wallet"
    )

    fraud_score: float = Field(
        default=0.0, ge=0.0, le=100.0, description="Fraud risk score (0-100)"
    )
    fraud_action: str = Field(
        default="ALLOW", description="Action: ALLOW, REVIEW, DECLINE"
    )
    fraud_signals: Dict[str, Any] = Field(
        default_factory=dict, description="Fraud detection signals"
    )

    authorization_code: Optional[str] = Field(
        default=None, description="Authorization code from processor"
    )
    capture_status: str = Field(
        default="pending", description="Status: pending, captured, voided, refunded"
    )

    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional merchant metadata"
    )
    created_at: Optional[str] = Field(
        default_factory=lambda: datetime.now(timezone.utc)
        .isoformat()
        .replace("+00:00", "Z"),
        description="Creation timestamp",
    )

    @field_validator("currency", "settlement_currency")
    @classmethod
    def validate_currency(cls, v: str) -> str:
        if len(v) != 3 or not v.isupper():
            raise ValueError("Currency must be 3-letter ISO 4217 code")
        return v

    @field_validator("fraud_action")
    @classmethod
    def validate_fraud_action(cls, v: str) -> str:
        if v not in ["ALLOW", "REVIEW", "DECLINE"]:
            raise ValueError("fraud_action must be ALLOW, REVIEW, or DECLINE")
        return v

    @field_validator("capture_status")
    @classmethod
    def validate_capture_status(cls, v: str) -> str:
        if v not in ["pending", "captured", "voided", "refunded"]:
            raise ValueError(
                "capture_status must be pending, captured, voided, or refunded"
            )
        return v

    model_config = ConfigDict(
        populate_by_name=True,
        use_enum_values=True,
        validate_assignment=True,
        extra="allow",
    )
