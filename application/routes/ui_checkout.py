import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from quart import Blueprint, jsonify, request
from quart.typing import ResponseReturnValue
from quart_schema import operation_id, tag

from application.entity.cart import Cart
from services.services import get_entity_service

logger = logging.getLogger(__name__)

ui_checkout_bp = Blueprint("ui_checkout", __name__, url_prefix="/ui/checkout")


def _get_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


@ui_checkout_bp.route("/<cart_id>", methods=["POST"])
@tag(["checkout"])
@operation_id("checkout")
async def checkout(cart_id: str) -> ResponseReturnValue:
    """Attach guest contact to cart and set to CHECKING_OUT"""
    try:
        data = await request.get_json()
        guest_contact = data.get("guestContact", {})

        service = get_entity_service()

        result = await service.get_by_id(
            entity_id=cart_id,
            entity_class=Cart.ENTITY_NAME,
            entity_version=str(Cart.ENTITY_VERSION),
        )

        if not result:
            return jsonify({"error": "Cart not found"}), 404

        cart_data = result.data.model_dump(by_alias=True)
        cart_data["guestContact"] = guest_contact
        cart_data["status"] = "CHECKING_OUT"
        cart_data["updatedAt"] = _get_timestamp()

        response = await service.update(
            entity_id=cart_id,
            entity=cart_data,
            entity_class=Cart.ENTITY_NAME,
            entity_version=str(Cart.ENTITY_VERSION),
        )

        result_data = response.data.model_dump(by_alias=True)
        return jsonify(result_data), 200

    except Exception as e:
        logger.exception("Error during checkout: %s", str(e))
        return jsonify({"error": str(e)}), 500
