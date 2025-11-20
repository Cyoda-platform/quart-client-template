# entity/order/version_1/order.py

"""
Order entity for Cyoda Client Application

Represents an order with items, customer information, and total amount calculation.
The totalAmount is calculated by the OrderProcessor based on item quantities and prices.
"""

from datetime import datetime, timezone
from typing import Any, ClassVar, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from common.entity.cyoda_entity import CyodaEntity


class OrderItem(BaseModel):
    """Represents an item within an order."""
    
    product_id: str = Field(..., alias="productId", description="Product identifier")
    quantity: int = Field(..., description="Quantity of the product")
    price: float = Field(..., description="Price per unit")
    
    @field_validator("quantity")
    @classmethod
    def validate_quantity(cls, v: int) -> int:
        """Validate quantity is greater than 0."""
        if v <= 0:
            raise ValueError("Quantity must be greater than 0")
        return v
    
    @field_validator("price")
    @classmethod
    def validate_price(cls, v: float) -> float:
        """Validate price is non-negative."""
        if v < 0:
            raise ValueError("Price must be non-negative")
        return v


class Order(CyodaEntity):
    """
    Order entity representing a customer order with items and total amount.
    
    The totalAmount is calculated automatically by the OrderProcessor
    based on the sum of (quantity * price) for all items.
    """
    
    # Entity constants
    ENTITY_NAME: ClassVar[str] = "Order"
    ENTITY_VERSION: ClassVar[int] = 1
    
    # Business identifier (using entity_id from CyodaEntity as the order ID)
    customer_id: str = Field(..., alias="customerId", description="Customer identifier")
    
    # Order items
    items: List[OrderItem] = Field(..., description="List of order items")
    
    # Order status
    status: str = Field(default="pending", description="Order status")
    
    # Total amount (calculated by processor)
    total_amount: float = Field(default=0.0, alias="totalAmount", description="Total order amount")
    
    # Creation timestamp (override from CyodaEntity to use alias)
    created_at: Optional[str] = Field(
        default_factory=lambda: datetime.now(timezone.utc)
        .isoformat()
        .replace("+00:00", "Z"),
        alias="createdAt",
        description="Timestamp when the order was created (ISO 8601 format)",
    )
    
    # Allowed status values
    ALLOWED_STATUSES: ClassVar[List[str]] = [
        "pending",
        "confirmed", 
        "processing",
        "shipped",
        "delivered",
        "cancelled"
    ]
    
    @field_validator("items")
    @classmethod
    def validate_items_not_empty(cls, v: List[OrderItem]) -> List[OrderItem]:
        """Validate that items list is not empty."""
        if not v or len(v) == 0:
            raise ValueError("Order must have at least one item")
        return v
    
    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        """Validate status is one of allowed values."""
        if v not in cls.ALLOWED_STATUSES:
            raise ValueError(f"Status must be one of: {cls.ALLOWED_STATUSES}")
        return v
    
    @field_validator("customer_id")
    @classmethod
    def validate_customer_id(cls, v: str) -> str:
        """Validate customer_id is not empty."""
        if not v or len(v.strip()) == 0:
            raise ValueError("Customer ID must be non-empty")
        return v.strip()
    
    def calculate_total(self) -> float:
        """Calculate total amount from items."""
        return sum(item.quantity * item.price for item in self.items)
    
    def update_total_amount(self) -> None:
        """Update the total_amount field based on current items."""
        self.total_amount = self.calculate_total()
    
    def is_cancellable(self) -> bool:
        """Check if order can be cancelled."""
        return self.status in ["pending", "confirmed"]
    
    def to_api_response(self) -> Dict[str, Any]:
        """Convert to API response format."""
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
