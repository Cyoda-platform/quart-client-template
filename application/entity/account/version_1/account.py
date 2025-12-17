from typing import ClassVar, Optional

from pydantic import Field

from common.entity.cyoda_entity import CyodaEntity


class Account(CyodaEntity):
    ENTITY_NAME: ClassVar[str] = "Account"
    ENTITY_VERSION: ClassVar[int] = 1

    account_id: str = Field(..., description="Unique business ID for the account")
    owner: str = Field(..., description="Name of the account owner")
    balance: float = Field(default=0.0, description="Cash balance")
    currency: str = Field(default="USD", description="Account currency")
    is_active: bool = Field(default=True, description="Is account active")
