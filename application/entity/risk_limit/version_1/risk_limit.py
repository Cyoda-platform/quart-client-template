from typing import ClassVar

from pydantic import Field

from common.entity.cyoda_entity import CyodaEntity


class RiskLimit(CyodaEntity):
    ENTITY_NAME: ClassVar[str] = "RiskLimit"
    ENTITY_VERSION: ClassVar[int] = 1

    account_id: str = Field(..., description="Account ID this limit applies to")
    limit_type: str = Field(..., description="Type of limit (e.g. POSITION_LIMIT)")
    threshold: float = Field(..., description="Limit threshold value")
    period: str = Field(default="DAILY", description="Time period (DAILY, INTRADAY)")
