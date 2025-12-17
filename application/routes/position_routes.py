from typing import Any, Dict, Tuple

from quart import Blueprint, jsonify, request

from application.entity.position.version_1.position import Position
from services.services import get_entity_service

position_routes = Blueprint("position_routes", __name__, url_prefix="/api/positions")


@position_routes.route("/", methods=["POST"])
async def create_position() -> Tuple[Dict[str, Any], int]:
    """
    Creates a new position.
    """
    data = await request.get_json()
    entity_service = get_entity_service()
    position = await entity_service.save(
        data, Position.ENTITY_NAME, Position.ENTITY_VERSION
    )
    return position.data.model_dump(), 201


@position_routes.route("/<entity_id>", methods=["GET"])
async def get_position(entity_id: str) -> Tuple[Dict[str, Any], int]:
    """
    Retrieves a position by its ID.
    """
    entity_service = get_entity_service()
    position = await entity_service.get_by_id(
        entity_id, Position.ENTITY_NAME, Position.ENTITY_VERSION
    )
    if position:
        return position.data.model_dump(), 200
    return {}, 404


@position_routes.route("/<entity_id>", methods=["PUT"])
async def update_position(entity_id: str) -> Tuple[Dict[str, Any], int]:
    """
    Updates a position by applying a transition.
    """
    data = await request.get_json()
    transition = data.get("transition")
    if not transition:
        return {"error": "transition is required"}, 400

    entity_service = get_entity_service()
    position = await entity_service.execute_transition(
        entity_id, transition, Position.ENTITY_NAME, Position.ENTITY_VERSION
    )
    if position:
        return position.data.model_dump(), 200
    return {}, 404
