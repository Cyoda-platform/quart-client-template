from pydantic import Field
from common.entity.cyoda_entity import CyodaEntity
from typing import Dict, Any, Optional

class AuditEvent(CyodaEntity):
    """Represents an audit event within the system."""
    
    ENTITY_NAME: str = "AuditEvent"
    ENTITY_VERSION: int = 1
    
    event_id: str = Field(..., description="Unique business identifier for the audit event")
    timestamp: str = Field(..., description="Timestamp of the event (ISO 8601 format)")
    user_id: Optional[str] = Field(None, description="Identifier of the user performing the action")
    action: str = Field(..., description="The action performed (e.g., create, update, delete)")
    target_entity_type: Optional[str] = Field(None, description="The type of entity affected by the action")
    target_entity_id: Optional[str] = Field(None, description="The identifier of the entity affected by the action")
    details: Dict[str, Any] = Field({}, description="Additional details about the event, typically a JSON object")
