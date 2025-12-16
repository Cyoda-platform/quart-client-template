from quart import Blueprint, request
from services.services import get_entity_service
from application.entity.execution_report.version_1.ExecutionReport import ExecutionReport

bp = Blueprint("execution_report", __name__, url_prefix="/ui/execution_report")

@bp.route("/", methods=["POST"])
async def create_execution_report():
    """Create new execution report."""
    entity_service = get_entity_service()
    data = await request.get_json()
    
    entity = ExecutionReport(**data)
    
    result = await entity_service.create(entity)
    
    return {"id": result.id}
