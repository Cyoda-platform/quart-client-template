import logging
from typing import Any, Dict

from quart import Blueprint
from quart.typing import ResponseReturnValue
from quart_schema import operation_id, tag, validate

from application.entity.venue.version_1.venue import Venue
from services.services import get_entity_service

logger = logging.getLogger(__name__)

venues_bp = Blueprint("venues", __name__, url_prefix="/api/venues")


def _to_entity_dict(data: Any) -> Dict[str, Any]:
    return data.model_dump(by_alias=True) if hasattr(data, "model_dump") else data


@venues_bp.route("", methods=["POST"])
@tag(["venues"])
@operation_id("create_venue")
@validate(request=Venue, responses={201: (Dict[str, Any], None)})
async def create_venue(data: Venue) -> ResponseReturnValue:
    """Create a new venue"""
    try:
        entity_data = data.model_dump(by_alias=True)
        response = await get_entity_service().save(
            entity=entity_data,
            entity_class=Venue.ENTITY_NAME,
            entity_version=str(Venue.ENTITY_VERSION),
        )
        logger.info(f"Created venue {response.metadata.id}")
        return _to_entity_dict(response.data), 201
    except Exception as e:
        logger.exception(f"Error creating venue: {str(e)}")
        return {"error": str(e)}, 400


@venues_bp.route("/<venue_id>", methods=["GET"])
@tag(["venues"])
@operation_id("get_venue")
@validate(responses={200: (Dict[str, Any], None)})
async def get_venue(venue_id: str) -> ResponseReturnValue:
    """Get venue by ID"""
    try:
        response = await get_entity_service().get_by_id(
            entity_id=venue_id,
            entity_class=Venue.ENTITY_NAME,
            entity_version=str(Venue.ENTITY_VERSION),
        )
        if not response:
            return {"error": "Venue not found"}, 404
        return _to_entity_dict(response.data), 200
    except Exception as e:
        logger.exception(f"Error getting venue: {str(e)}")
        return {"error": str(e)}, 400


@venues_bp.route("", methods=["GET"])
@tag(["venues"])
@operation_id("list_venues")
@validate(responses={200: (Dict[str, Any], None)})
async def list_venues() -> ResponseReturnValue:
    """List all venues"""
    try:
        entities = await get_entity_service().find_all(
            entity_class=Venue.ENTITY_NAME,
            entity_version=str(Venue.ENTITY_VERSION),
        )
        entity_list = [_to_entity_dict(r.data) for r in entities]
        return {"venues": entity_list, "total": len(entity_list)}, 200
    except Exception as e:
        logger.exception(f"Error listing venues: {str(e)}")
        return {"error": str(e)}, 400
