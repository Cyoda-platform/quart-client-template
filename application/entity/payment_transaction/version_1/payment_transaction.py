"""
PaymentTransaction Entity for Enterprise Payment Processing System

Represents a payment transaction with multi-currency support, fraud detection,
PCI DSS compliance, and comprehensive audit trail capabilities.
"""

from datetime import datetime, timezone
from typing import Any, ClassVar, Dict, List, Optional

from pydantic import ConfigDict, Field, field_validator, model_validator

from common.entity.cyoda_entity import CyodaEntity


class PaymentTransaction(CyodaEntity):
    """
    PaymentTransaction represents a payment transaction in the system.

    Inherits from CyodaEntity to get common fields like entity_id, state, etc.
    The state field manages workflow states: initial_state -> created -> validated ->
    fraud_checked -> settled -> completed
    """

    # Entity constants
    ENTITY_NAME: ClassVar[str] = "PaymentTransaction"
    ENTITY_VERSION: ClassVar[int] = 1

    # Core transaction fields
    transaction_id: str = Field(..., description="Unique transaction identifier")
    amount: float = Field(..., gt=0, description="Transaction amount")
    currency: str = Field(..., description="ISO 4217 currency code (e.g., USD, EUR)")
    merchant_id: str = Field(..., description="Merchant identifier")
    customer_id: str = Field(..., description="Customer identifier")

    # Transaction details
    description: Optional[str] = Field(
        default=None, description="Transaction description"
    )
    reference_number: Optional[str] = Field(
        default=None, description="External reference number"
    )

    # Fraud detection fields
    fraud_score: Optional[float] = Field(
        default=None,
        ge=0,
        le=100,
        alias="fraudScore",
        description="Fraud detection score (0-100)",
    )
    fraud_status: Optional[str] = Field(
        default=None,
        alias="fraudStatus",
        description="Fraud status: LOW_RISK, MEDIUM_RISK, HIGH_RISK",
    )
    fraud_checks_performed: Optional[List[str]] = Field(
        default=None,
        alias="fraudChecksPerformed",
        description="List of fraud checks performed",
    )

    # PCI DSS compliance fields
    pci_compliant: Optional[bool] = Field(
        default=None,
        alias="pciCompliant",
        description="Whether transaction is PCI DSS compliant",
    )
    masked_card_number: Optional[str] = Field(
        default=None,
        alias="maskedCardNumber",
        description="Masked card number (last 4 digits only)",
    )

    # Settlement fields
    settlement_id: Optional[str] = Field(
        default=None,
        alias="settlementId",
        description="Associated settlement batch ID",
    )
    settlement_date: Optional[str] = Field(
        default=None,
        alias="settlementDate",
        description="Settlement date (ISO 8601 format)",
    )

    # Timestamps
    created_at: Optional[str] = Field(
        default_factory=lambda: datetime.now(timezone.utc)
        .isoformat()
        .replace("+00:00", "Z"),
        alias="createdAt",
        description="Timestamp when transaction was created",
    )
    updated_at: Optional[str] = Field(
        default=None,
        alias="updatedAt",
        description="Timestamp when transaction was last updated",
    )

    # Audit trail
    audit_log_ids: Optional[List[str]] = Field(
        default=None,
        alias="auditLogIds",
        description="List of associated audit log IDs",
    )

    # Validation rules
    ALLOWED_CURRENCIES: ClassVar[List[str]] = [
        "USD",
        "EUR",
        "GBP",
        "JPY",
        "CAD",
        "AUD",
        "CHF",
        "CNY",
    ]
    FRAUD_STATUSES: ClassVar[List[str]] = ["LOW_RISK", "MEDIUM_RISK", "HIGH_RISK"]

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, v: str) -> str:
        """Validate currency code"""
        if v not in cls.ALLOWED_CURRENCIES:
            raise ValueError(f"Currency must be one of: {cls.ALLOWED_CURRENCIES}")
        return v

    @field_validator("fraud_status")
    @classmethod
    def validate_fraud_status(cls, v: Optional[str]) -> Optional[str]:
        """Validate fraud status"""
        if v is not None and v not in cls.FRAUD_STATUSES:
            raise ValueError(f"Fraud status must be one of: {cls.FRAUD_STATUSES}")
        return v

    @model_validator(mode="after")
    def validate_business_logic(self) -> "PaymentTransaction":
        """Validate business logic rules"""
        if self.amount <= 0:
            raise ValueError("Amount must be greater than 0")
        if self.fraud_score is not None and (
            self.fraud_score < 0 or self.fraud_score > 100
        ):
            raise ValueError("Fraud score must be between 0 and 100")
        return self

    def update_timestamp(self) -> None:
        """Update the updated_at timestamp to current time"""
        self.updated_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    def set_fraud_detection_result(
        self, fraud_score: float, fraud_status: str, checks: List[str]
    ) -> None:
        """Set fraud detection results"""
        self.fraud_score = fraud_score
        self.fraud_status = fraud_status
        self.fraud_checks_performed = checks
        self.update_timestamp()

    def mark_pci_compliant(self, masked_card: str) -> None:
        """Mark transaction as PCI compliant"""
        self.pci_compliant = True
        self.masked_card_number = masked_card
        self.update_timestamp()

    def associate_settlement(self, settlement_id: str, settlement_date: str) -> None:
        """Associate transaction with a settlement batch"""
        self.settlement_id = settlement_id
        self.settlement_date = settlement_date
        self.update_timestamp()

    def add_audit_log(self, audit_log_id: str) -> None:
        """Add an audit log ID to the transaction"""
        if self.audit_log_ids is None:
            self.audit_log_ids = []
        if audit_log_id not in self.audit_log_ids:
            self.audit_log_ids.append(audit_log_id)
        self.update_timestamp()

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
