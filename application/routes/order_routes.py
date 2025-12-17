from typing import Any, Dict, Tuple

from quart import Blueprint, request

from application.entity.order.version_1.order import Order
from services.services import get_entity_service

order_routes = Blueprint("order_routes", __name__, url_prefix="/api/orders")


@order_routes.route("/", methods=["POST"])
async def create_order() -> Tuple[Dict[str, Any], int]:
    """
    Creates a new order.
    """
    data = await request.get_json()
    entity_service = get_entity_service()
    order = await entity_service.save(data, Order.ENTITY_NAME, Order.ENTITY_VERSION)
    return order.data.model_dump(), 201


@order_routes.route("/<entity_id>", methods=["GET"])
async def get_order(entity_id: str) -> Tuple[Dict[str, Any], int]:
    """
    Retrieves an order by its ID.
    """
    entity_service = get_entity_service()
    order = await entity_service.get_by_id(
        entity_id, Order.ENTITY_NAME, Order.ENTITY_VERSION
    )
    if order:
        return order.data.model_dump(), 200
    return {}, 404


@order_routes.route("/<entity_id>", methods=["PUT"])
async def update_order(entity_id: str) -> Tuple[Dict[str, Any], int]:
    """
    Updates an order by applying a transition.
    """
    data = await request.get_json()
    transition = data.get("transition")
    if not transition:
        return {"error": "transition is required"}, 400

    entity_service = get_entity_service()
    order = await entity_service.execute_transition(
        entity_id, transition, Order.ENTITY_NAME, Order.ENTITY_VERSION
    )
    if order:
        return order.data.model_dump(), 200
    return {}, 404
