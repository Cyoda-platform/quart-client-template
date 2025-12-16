from quart import Blueprint, request
from services.services import get_entity_service
from application.entity.market_venue.version_1.MarketVenue import MarketVenue

bp = Blueprint("market_venue", __name__, url_prefix="/ui/market_venue")

@bp.route("/", methods=["POST"])
async def register_market_venue():
    """Register new market venue."""
    entity_service = get_entity_service()
    data = await request.get_json()
    
    entity = MarketVenue(**data)
    
    result = await entity_service.create(entity)
    
    return {"id": result.id}

@bp.route("/<entity_id>", methods=["PUT"])
async def update_market_venue(entity_id: str):
    """Update market venue."""
    entity_service = get_entity_service()
    data = await request.get_json()
    
    existing = await entity_service.get_by_id(
        entity_id, 
        MarketVenue.ENTITY_NAME, 
        str(MarketVenue.ENTITY_VERSION)
    )
    
    updated = existing.data.model_copy(update=data)
    
    result = await entity_service.update(updated, transition="update_venue")
    
    return {"id": result.id}
