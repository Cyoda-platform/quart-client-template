from typing import ClassVar

from pydantic import ConfigDict, Field

from common.entity.cyoda_entity import CyodaEntity


class Account(CyodaEntity):
    """
    Account represents a trading account.
    
    Manages account-level information including balance and currency.
    """

    ENTITY_NAME: ClassVar[str] = "Account"
    ENTITY_VERSION: ClassVar[int] = 1

    account_id: str = Field(..., description="Business identifier for the account")
    name: str = Field(..., description="Account name")
    margin_balance: float = Field(..., description="Available margin balance")
    currency: str = Field(..., description="Account currency")
    status: str = Field(default="Active", description="Account status")
    total_balance: float = Field(default=0.0, description="Total account balance")

    model_config = ConfigDict(
        populate_by_name=True,
        use_enum_values=True,
        validate_assignment=True,
        extra="allow",
    )

