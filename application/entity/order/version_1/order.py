"""
Order entity for Cyoda Client Application

Represents an order with items, total amount, and lifecycle management
including payment processing and cancellation with refunds.
"""

from decimal import Decimal
from typing import Any, ClassVar, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from common.entity.cyoda_entity import CyodaEntity


class OrderItem(BaseModel):
    """Represents an item in an order."""
    
    item_id: str = Field(..., description="Unique identifier for the item")
    name: str = Field(..., description="Name of the item")
    quantity: int = Field(..., gt=0, description="Quantity of the item")
    unit_price: Decimal = Field(..., gt=0, description="Unit price of the item")
    total_price: Decimal = Field(..., gt=0, description="Total price for this item")
    
    @field_validator("total_price")
    @classmethod
    def validate_total_price(cls, v: Decimal, info) -> Decimal:
        """Validate that total_price equals quantity * unit_price."""
        if info.data:
            quantity = info.data.get("quantity", 0)
            unit_price = info.data.get("unit_price", Decimal("0"))
            expected_total = Decimal(str(quantity)) * unit_price
            if v != expected_total:
                raise ValueError(f"Total price {v} does not match quantity {quantity} * unit_price {unit_price}")
        return v


class Order(CyodaEntity):
    """
    Order entity representing a customer order with items, payment processing,
    and cancellation capabilities.
    """

    # Entity constants
    ENTITY_NAME: ClassVar[str] = "Order"
    ENTITY_VERSION: ClassVar[int] = 1

    # Required business fields
    order_id: str = Field(..., description="Business identifier for the order")
    items: List[OrderItem] = Field(..., min_length=1, description="List of items in the order")
    total: Decimal = Field(..., gt=0, description="Total amount of the order")
    
    # Optional fields
    customer_id: Optional[str] = Field(None, description="Customer identifier")
    payment_status: Optional[str] = Field(None, description="Payment processing status")
    payment_transaction_id: Optional[str] = Field(None, description="Payment transaction identifier")
    cancel_reason: Optional[str] = Field(None, description="Reason for cancellation (required when cancelling)")
    refund_transaction_id: Optional[str] = Field(None, description="Refund transaction identifier")
    
    @field_validator("order_id")
    @classmethod
    def validate_order_id(cls, v: str) -> str:
        """Validate order_id is non-empty."""
        if not v or len(v.strip()) == 0:
            raise ValueError("Order ID must be non-empty")
        return v.strip()
    
    @field_validator("total")
    @classmethod
    def validate_total_matches_items(cls, v: Decimal, info) -> Decimal:
        """Validate that total matches sum of item totals."""
        if info.data and "items" in info.data:
            items = info.data["items"]
            if items:
                items_total = sum(item.total_price for item in items)
                if v != items_total:
                    raise ValueError(f"Order total {v} does not match sum of item totals {items_total}")
        return v
    
    @field_validator("cancel_reason")
    @classmethod
    def validate_cancel_reason(cls, v: Optional[str]) -> Optional[str]:
        """Validate cancel_reason when provided."""
        if v is not None:
            if len(v.strip()) == 0:
                raise ValueError("Cancel reason cannot be empty when provided")
            if len(v) > 500:
                raise ValueError("Cancel reason must be at most 500 characters")
            return v.strip()
        return v
    
    def calculate_total(self) -> Decimal:
        """Calculate total from items."""
        return sum(item.total_price for item in self.items)
    
    def is_cancellable(self) -> bool:
        """Check if order can be cancelled (not already cancelled)."""
        return self.meta.state not in ["cancelled"]
    
    def requires_refund(self) -> bool:
        """Check if order requires refund processing."""
        return (
            self.payment_status == "completed" 
            and self.payment_transaction_id is not None
        )

    model_config = ConfigDict(
        populate_by_name=True,
        use_enum_values=True,
        validate_assignment=True,
        extra="allow",
    )
