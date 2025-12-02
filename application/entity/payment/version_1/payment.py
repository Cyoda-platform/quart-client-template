from typing import ClassVar, Optional

from pydantic import ConfigDict, Field

from common.entity.cyoda_entity import CyodaEntity


class Payment(CyodaEntity):
    ENTITY_NAME: ClassVar[str] = "Payment"
    ENTITY_VERSION: ClassVar[int] = 1

    paymentId: str = Field(..., description="Payment ID")
    cartId: str = Field(..., description="Associated cart ID")
    amount: float = Field(..., description="Payment amount")
    status: str = Field(default="INITIATED", description="Payment status")
    provider: str = Field(default="DUMMY", description="Payment provider")
    createdAt: Optional[str] = Field(None, description="Creation timestamp")
    updatedAt: Optional[str] = Field(None, description="Update timestamp")

    model_config = ConfigDict(
        populate_by_name=True,
        use_enum_values=True,
        validate_assignment=True,
        extra="allow",
    )
