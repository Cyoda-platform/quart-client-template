from datetime import datetime, timezone
from typing import ClassVar, Optional

from pydantic import ConfigDict, Field, field_validator

from common.entity.cyoda_entity import CyodaEntity


class Venue(CyodaEntity):
    """
    Venue represents an exchange or trading venue.
    State transitions: initial_state -> active -> inactive
    """

    ENTITY_NAME: ClassVar[str] = "Venue"
    ENTITY_VERSION: ClassVar[int] = 1

    venue_name: str = Field(..., description="Venue name (e.g., NYSE, NASDAQ)")
    venue_code: str = Field(..., description="Venue code (e.g., NYS, NAS)")
    venue_type: str = Field(..., description="Venue type: EXCHANGE, OTC, SIMULATION")
    region: str = Field(..., description="Geographic region")
    trading_hours_open: str = Field(..., description="Market open time (HH:MM:SS)")
    trading_hours_close: str = Field(..., description="Market close time (HH:MM:SS)")
    is_operational: bool = Field(default=True, description="Venue operational status")
    connection_status: str = Field(default="DISCONNECTED", description="Connection status")
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        description="Venue creation timestamp"
    )
    updated_at: Optional[str] = Field(None, description="Last update timestamp")

    @field_validator("venue_type")
    @classmethod
    def validate_venue_type(cls, v: str) -> str:
        if v not in ["EXCHANGE", "OTC", "SIMULATION"]:
            raise ValueError("venue_type must be EXCHANGE, OTC, or SIMULATION")
        return v

    @field_validator("connection_status")
    @classmethod
    def validate_connection_status(cls, v: str) -> str:
        if v not in ["CONNECTED", "DISCONNECTED", "ERROR"]:
            raise ValueError("connection_status must be CONNECTED, DISCONNECTED, or ERROR")
        return v

    model_config = ConfigDict(
        populate_by_name=True,
        use_enum_values=True,
        validate_assignment=True,
        extra="allow",
    )

