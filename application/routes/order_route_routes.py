from quart import Blueprint, request
from services.services import get_entity_service
from application.entity.order_route.version_1.OrderRoute import OrderRoute

bp = Blueprint("order_route", __name__, url_prefix="/ui/order_route")

@bp.route("/", methods=["POST"])
async def create_order_route():
    """Create new order route."""
    entity_service = get_entity_service()
    data = await request.get_json()
    
    entity = OrderRoute(**data)
    
    result = await entity_service.create(entity)
    
    return {"id": result.id}

@bp.route("/<entity_id>", methods=["PUT"])
async def update_order_route(entity_id: str):
    """Update order route."""
    entity_service = get_entity_service()
    data = await request.get_json()
    
    existing = await entity_service.get_by_id(
        entity_id, 
        OrderRoute.ENTITY_NAME, 
        str(OrderRoute.ENTITY_VERSION)
    )
    
    updated = existing.data.model_copy(update=data)
    
    result = await entity_service.update(updated, transition="update_route")
    
    return {"id": result.id}
