from quart import Blueprint, request
from services.services import get_entity_service
from application.entity.audit_event.version_1.AuditEvent import AuditEvent

bp = Blueprint("audit_event", __name__, url_prefix="/ui/audit_event")

@bp.route("/", methods=["POST"])
async def record_audit_event():
    """Record new audit event."""
    entity_service = get_entity_service()
    data = await request.get_json()
    
    entity = AuditEvent(**data)
    
    result = await entity_service.create(entity)
    
    return {"id": result.id}
