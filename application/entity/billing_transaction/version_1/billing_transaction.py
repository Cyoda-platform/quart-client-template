"""
BillingTransaction entity for healthcare application.

Represents a billing transaction for healthcare services with payment
tracking and invoice management.
"""

from datetime import datetime, timezone
from typing import ClassVar, List, Optional

from pydantic import ConfigDict, Field, field_validator

from common.entity.cyoda_entity import CyodaEntity


class BillingTransaction(CyodaEntity):
    """
    BillingTransaction entity representing a billing transaction for healthcare services.
    
    Manages payment processing, status tracking, and invoice information
    for patient billing and payment management.
    """

    # Entity constants
    ENTITY_NAME: ClassVar[str] = "BillingTransaction"
    ENTITY_VERSION: ClassVar[int] = 1

    # Business ID field
    transaction_id: str = Field(..., description="Business identifier for the billing transaction")

    # Transaction details
    patient_id: str = Field(..., description="ID of the patient")
    amount_cents: int = Field(..., description="Transaction amount in cents")
    currency: str = Field(default="USD", description="Currency code (e.g., USD, EUR)")
    status: str = Field(..., description="Transaction status")
    transaction_created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        description="When the transaction was created (ISO 8601)"
    )
    paid_at: Optional[str] = Field(default=None, description="When the transaction was paid (ISO 8601)")
    invoice_url: Optional[str] = Field(default=None, description="URL to the invoice document")

    # Valid transaction statuses
    VALID_STATUSES: ClassVar[List[str]] = [
        "pending",
        "paid",
        "failed"
    ]

    # Valid currency codes (subset of common ones)
    VALID_CURRENCIES: ClassVar[List[str]] = [
        "USD", "EUR", "GBP", "CAD", "AUD", "JPY", "CHF", "CNY"
    ]

    @field_validator("patient_id")
    @classmethod
    def validate_patient_id(cls, v: str) -> str:
        """Validate patient ID."""
        if not v or len(v.strip()) == 0:
            raise ValueError("Patient ID must be non-empty")
        return v.strip()

    @field_validator("amount_cents")
    @classmethod
    def validate_amount_cents(cls, v: int) -> int:
        """Validate transaction amount in cents."""
        if v <= 0:
            raise ValueError("Amount in cents must be greater than 0")
        if v > 100000000:  # $1M limit
            raise ValueError("Amount in cents must be at most 100,000,000 (1 million dollars)")
        return v

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, v: str) -> str:
        """Validate currency code."""
        if not v or len(v.strip()) == 0:
            raise ValueError("Currency must be non-empty")
        
        currency_upper = v.strip().upper()
        if currency_upper not in cls.VALID_CURRENCIES:
            raise ValueError(f"Currency must be one of: {cls.VALID_CURRENCIES}")
        
        return currency_upper

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        """Validate transaction status."""
        if not v or len(v.strip()) == 0:
            raise ValueError("Status must be non-empty")
        
        status_lower = v.strip().lower()
        if status_lower not in cls.VALID_STATUSES:
            raise ValueError(f"Status must be one of: {cls.VALID_STATUSES}")
        
        return status_lower

    @field_validator("transaction_created_at")
    @classmethod
    def validate_transaction_created_at(cls, v: str) -> str:
        """Validate transaction creation datetime."""
        if not v or len(v.strip()) == 0:
            raise ValueError("Transaction created at must be non-empty")
        
        try:
            # Parse ISO 8601 datetime
            datetime.fromisoformat(v.strip().replace('Z', '+00:00'))
        except ValueError:
            raise ValueError("Transaction created at must be in ISO 8601 format")
        
        return v.strip()

    @field_validator("paid_at")
    @classmethod
    def validate_paid_at(cls, v: Optional[str]) -> Optional[str]:
        """Validate payment datetime."""
        if v is None:
            return v
        
        if len(v.strip()) == 0:
            return None
        
        try:
            # Parse ISO 8601 datetime
            datetime.fromisoformat(v.strip().replace('Z', '+00:00'))
        except ValueError:
            raise ValueError("Paid at must be in ISO 8601 format")
        
        return v.strip()

    @field_validator("invoice_url")
    @classmethod
    def validate_invoice_url(cls, v: Optional[str]) -> Optional[str]:
        """Validate invoice URL."""
        if v is None:
            return v
        
        if len(v.strip()) == 0:
            return None
        
        # Basic URL validation
        url = v.strip()
        if not (url.startswith("http://") or url.startswith("https://")):
            raise ValueError("Invoice URL must start with http:// or https://")
        
        if len(url) > 500:
            raise ValueError("Invoice URL must be at most 500 characters long")
        
        return url

    def get_amount_dollars(self) -> float:
        """Get transaction amount in dollars."""
        return self.amount_cents / 100.0

    def is_paid(self) -> bool:
        """Check if transaction is paid."""
        return self.status == "paid"

    def is_pending(self) -> bool:
        """Check if transaction is pending."""
        return self.status == "pending"

    def is_failed(self) -> bool:
        """Check if transaction failed."""
        return self.status == "failed"

    def mark_as_paid(self, paid_at: Optional[str] = None) -> None:
        """Mark transaction as paid."""
        self.status = "paid"
        if paid_at is None:
            self.paid_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        else:
            self.paid_at = paid_at

    def mark_as_failed(self) -> None:
        """Mark transaction as failed."""
        self.status = "failed"
        self.paid_at = None

    def has_invoice(self) -> bool:
        """Check if transaction has an invoice URL."""
        return self.invoice_url is not None and len(self.invoice_url.strip()) > 0

    def get_formatted_amount(self) -> str:
        """Get formatted amount with currency symbol."""
        amount_dollars = self.get_amount_dollars()
        if self.currency == "USD":
            return f"${amount_dollars:.2f}"
        elif self.currency == "EUR":
            return f"€{amount_dollars:.2f}"
        elif self.currency == "GBP":
            return f"£{amount_dollars:.2f}"
        else:
            return f"{amount_dollars:.2f} {self.currency}"

    model_config = ConfigDict(
        populate_by_name=True,
        use_enum_values=True,
        validate_assignment=True,
        extra="allow",
    )
