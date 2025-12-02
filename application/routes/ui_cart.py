import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from uuid import uuid4

from quart import Blueprint, jsonify, request
from quart.typing import ResponseReturnValue
from quart_schema import operation_id, tag, validate

from services.services import get_entity_service
from application.entity.cart import Cart

logger = logging.getLogger(__name__)

ui_cart_bp = Blueprint("ui_cart", __name__, url_prefix="/ui/cart")


def _get_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


@ui_cart_bp.route("", methods=["POST"])
@tag(["cart"])
@operation_id("create_or_get_cart")
async def create_or_get_cart() -> ResponseReturnValue:
    """Create or return existing cart"""
    try:
        service = get_entity_service()

        timestamp = _get_timestamp()
        cart_id = str(uuid4())

        cart = Cart(
            cartId=cart_id,
            status="NEW",
            lines=[],
            totalItems=0,
            grandTotal=0.0,
            createdAt=timestamp,
            updatedAt=timestamp,
        )

        cart_data = cart.model_dump(by_alias=True)

        response = await service.save(
            entity=cart_data,
            entity_class=Cart.ENTITY_NAME,
            entity_version=str(Cart.ENTITY_VERSION),
        )

        result = response.data.model_dump(by_alias=True)
        return jsonify(result), 201

    except Exception as e:
        logger.exception("Error creating cart: %s", str(e))
        return jsonify({"error": str(e)}), 500


@ui_cart_bp.route("/<cart_id>", methods=["GET"])
@tag(["cart"])
@operation_id("get_cart")
async def get_cart(cart_id: str) -> ResponseReturnValue:
    """Get cart by ID"""
    try:
        service = get_entity_service()

        result = await service.get_by_id(
            entity_id=cart_id,
            entity_class=Cart.ENTITY_NAME,
            entity_version=str(Cart.ENTITY_VERSION),
        )

        if not result:
            return jsonify({"error": "Cart not found"}), 404

        cart_data = result.data.model_dump(by_alias=True)
        return jsonify(cart_data), 200

    except Exception as e:
        logger.exception("Error getting cart %s: %s", cart_id, str(e))
        return jsonify({"error": str(e)}), 500


@ui_cart_bp.route("/<cart_id>/lines", methods=["POST"])
@tag(["cart"])
@operation_id("add_cart_line")
async def add_cart_line(cart_id: str) -> ResponseReturnValue:
    """Add or increment item in cart"""
    try:
        data = await request.get_json()
        sku = data.get("sku")
        qty = data.get("qty", 1)
        name = data.get("name", "")
        price = data.get("price", 0.0)

        service = get_entity_service()

        result = await service.get_by_id(
            entity_id=cart_id,
            entity_class=Cart.ENTITY_NAME,
            entity_version=str(Cart.ENTITY_VERSION),
        )

        if not result:
            return jsonify({"error": "Cart not found"}), 404

        cart = result.data
        cart_data = cart.model_dump(by_alias=True)

        existing_line = None
        for line in cart_data.get("lines", []):
            if line.get("sku") == sku:
                existing_line = line
                break

        if existing_line:
            existing_line["qty"] += qty
        else:
            cart_data["lines"].append(
                {"sku": sku, "name": name, "price": price, "qty": qty}
            )

        cart_data["updatedAt"] = _get_timestamp()

        response = await service.update(
            entity_id=cart_id,
            entity=cart_data,
            entity_class=Cart.ENTITY_NAME,
            transition="ADD_ITEM",
            entity_version=str(Cart.ENTITY_VERSION),
        )

        result_data = response.data.model_dump(by_alias=True)
        return jsonify(result_data), 200

    except Exception as e:
        logger.exception("Error adding cart line: %s", str(e))
        return jsonify({"error": str(e)}), 500


@ui_cart_bp.route("/<cart_id>/lines", methods=["PATCH"])
@tag(["cart"])
@operation_id("update_cart_line")
async def update_cart_line(cart_id: str) -> ResponseReturnValue:
    """Set or decrement item quantity (remove if qty=0)"""
    try:
        data = await request.get_json()
        sku = data.get("sku")
        qty = data.get("qty", 0)

        service = get_entity_service()

        result = await service.get_by_id(
            entity_id=cart_id,
            entity_class=Cart.ENTITY_NAME,
            entity_version=str(Cart.ENTITY_VERSION),
        )

        if not result:
            return jsonify({"error": "Cart not found"}), 404

        cart_data = result.data.model_dump(by_alias=True)

        if qty <= 0:
            cart_data["lines"] = [
                line for line in cart_data.get("lines", []) if line.get("sku") != sku
            ]
        else:
            for line in cart_data.get("lines", []):
                if line.get("sku") == sku:
                    line["qty"] = qty
                    break

        cart_data["updatedAt"] = _get_timestamp()

        response = await service.update(
            entity_id=cart_id,
            entity=cart_data,
            entity_class=Cart.ENTITY_NAME,
            transition="DECREMENT_ITEM" if qty > 0 else "REMOVE_ITEM",
            entity_version=str(Cart.ENTITY_VERSION),
        )

        result_data = response.data.model_dump(by_alias=True)
        return jsonify(result_data), 200

    except Exception as e:
        logger.exception("Error updating cart line: %s", str(e))
        return jsonify({"error": str(e)}), 500


@ui_cart_bp.route("/<cart_id>/open-checkout", methods=["POST"])
@tag(["cart"])
@operation_id("open_checkout")
async def open_checkout(cart_id: str) -> ResponseReturnValue:
    """Set cart to CHECKING_OUT state"""
    try:
        service = get_entity_service()

        result = await service.get_by_id(
            entity_id=cart_id,
            entity_class=Cart.ENTITY_NAME,
            entity_version=str(Cart.ENTITY_VERSION),
        )

        if not result:
            return jsonify({"error": "Cart not found"}), 404

        cart_data = result.data.model_dump(by_alias=True)
        cart_data["status"] = "CHECKING_OUT"
        cart_data["updatedAt"] = _get_timestamp()

        response = await service.update(
            entity_id=cart_id,
            entity=cart_data,
            entity_class=Cart.ENTITY_NAME,
            transition="OPEN_CHECKOUT",
            entity_version=str(Cart.ENTITY_VERSION),
        )

        result_data = response.data.model_dump(by_alias=True)
        return jsonify(result_data), 200

    except Exception as e:
        logger.exception("Error opening checkout: %s", str(e))
        return jsonify({"error": str(e)}), 500

