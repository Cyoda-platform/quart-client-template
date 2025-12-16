from quart import Blueprint, request
from services.services import get_entity_service
from application.entity.risk_limit_profile.version_1.RiskLimitProfile import RiskLimitProfile

bp = Blueprint("risk_limit_profile", __name__, url_prefix="/ui/risk_limit_profile")

@bp.route("/", methods=["POST"])
async def create_risk_limit_profile():
    """Create new risk limit profile."""
    entity_service = get_entity_service()
    data = await request.get_json()
    
    entity = RiskLimitProfile(**data)
    
    result = await entity_service.create(entity)
    
    return {"id": result.id}

@bp.route("/<entity_id>", methods=["PUT"])
async def update_risk_limit_profile(entity_id: str):
    """Update risk limit profile."""
    entity_service = get_entity_service()
    data = await request.get_json()
    
    existing = await entity_service.get_by_id(
        entity_id, 
        RiskLimitProfile.ENTITY_NAME, 
        str(RiskLimitProfile.ENTITY_VERSION)
    )
    
    updated = existing.data.model_copy(update=data)
    
    result = await entity_service.update(updated, transition="update_profile")
    
    return {"id": result.id}
