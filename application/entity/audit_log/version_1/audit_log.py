"""
AuditLog entity for trading platform.

Immutable event log for all system actions with full traceability
for regulatory compliance and forensic analysis.
"""

from typing import Any, ClassVar, Dict, Optional

from pydantic import Field

from common.entity.cyoda_entity import CyodaEntity


class AuditLog(CyodaEntity):
    """
    Represents an immutable audit log entry in the trading system.
    
    Manages log lifecycle: initial_state -> logged -> archived
    """

    ENTITY_NAME: ClassVar[str] = "AuditLog"
    ENTITY_VERSION: ClassVar[int] = 1

    event_type: str = Field(
        ..., alias="eventType", description="ORDER_CREATED, TRADE_EXECUTED, LIMIT_CHECKED, etc."
    )
    user_id: Optional[str] = Field(
        default=None, alias="userId", description="User who triggered event"
    )
    account_id: Optional[str] = Field(
        default=None, alias="accountId", description="Account affected"
    )
    entity_type: str = Field(
        ..., alias="entityType", description="Entity type (Order, Trade, Position, etc.)"
    )
    entity_id: str = Field(..., alias="entityId", description="Entity ID")
    action: str = Field(..., description="CREATE, UPDATE, DELETE, TRANSITION")
    old_values: Optional[Dict[str, Any]] = Field(
        default=None, alias="oldValues", description="Previous values"
    )
    new_values: Optional[Dict[str, Any]] = Field(
        default=None, alias="newValues", description="New values"
    )
    ip_address: Optional[str] = Field(
        default=None, alias="ipAddress", description="Source IP address"
    )
    timestamp: str = Field(..., description="Event timestamp")
    details: Optional[str] = Field(
        default=None, description="Additional details"
    )

    def is_logged(self) -> bool:
        return self.state == "logged"

