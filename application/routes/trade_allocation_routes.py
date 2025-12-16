from quart import Blueprint, request
from services.services import get_entity_service
from application.entity.trade_allocation.version_1.TradeAllocation import TradeAllocation

bp = Blueprint("trade_allocation", __name__, url_prefix="/ui/trade_allocation")

@bp.route("/", methods=["POST"])
async def create_trade_allocation():
    """Create new trade allocation."""
    entity_service = get_entity_service()
    data = await request.get_json()
    
    entity = TradeAllocation(**data)
    
    result = await entity_service.create(entity)
    
    return {"id": result.id}

@bp.route("/<entity_id>", methods=["PUT"])
async def update_trade_allocation(entity_id: str):
    """Update trade allocation."""
    entity_service = get_entity_service()
    data = await request.get_json()
    
    existing = await entity_service.get_by_id(
        entity_id, 
        TradeAllocation.ENTITY_NAME, 
        str(TradeAllocation.ENTITY_VERSION)
    )
    
    updated = existing.data.model_copy(update=data)
    
    result = await entity_service.update(updated, transition="update_allocation")
    
    return {"id": result.id}
