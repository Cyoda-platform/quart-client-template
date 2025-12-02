import logging
from datetime import datetime, timezone
from uuid import uuid4

from quart import Blueprint, jsonify, request
from quart.typing import ResponseReturnValue
from quart_schema import operation_id, tag

from application.entity.cart import Cart
from application.entity.order import Order
from application.entity.payment import Payment
from services.services import get_entity_service

logger = logging.getLogger(__name__)

ui_order_bp = Blueprint("ui_order", __name__, url_prefix="/ui/order")


def _get_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _generate_ulid() -> str:
    """Generate a short ULID-like order number"""
    import random
    import time

    timestamp = int(time.time() * 1000)
    random_part = random.randint(100000, 999999)
    return f"{timestamp:x}{random_part:x}"[:12]


@ui_order_bp.route("/create", methods=["POST"])
@tag(["order"])
@operation_id("create_order")
async def create_order() -> ResponseReturnValue:
    """Create order from paid payment"""
    try:
        data = await request.get_json()
        payment_id = data.get("paymentId")
        cart_id = data.get("cartId")

        if not payment_id or not cart_id:
            return jsonify({"error": "paymentId and cartId are required"}), 400

        service = get_entity_service()

        payment_result = await service.get_by_id(
            entity_id=payment_id,
            entity_class=Payment.ENTITY_NAME,
            entity_version=str(Payment.ENTITY_VERSION),
        )

        if not payment_result:
            return jsonify({"error": "Payment not found"}), 404

        payment_data = payment_result.data.model_dump(by_alias=True)

        if payment_data.get("status") != "PAID":
            return jsonify({"error": "Payment is not in PAID status"}), 400

        cart_result = await service.get_by_id(
            entity_id=cart_id,
            entity_class=Cart.ENTITY_NAME,
            entity_version=str(Cart.ENTITY_VERSION),
        )

        if not cart_result:
            return jsonify({"error": "Cart not found"}), 404

        cart_data = cart_result.data.model_dump(by_alias=True)

        timestamp = _get_timestamp()
        order_id = str(uuid4())
        order_number = _generate_ulid()

        order = Order(
            orderId=order_id,
            orderNumber=order_number,
            status="WAITING_TO_FULFILL",
            lines=cart_data.get("lines", []),
            totals={
                "items": cart_data.get("totalItems", 0),
                "grand": cart_data.get("grandTotal", 0.0),
            },
            guestContact=cart_data.get("guestContact"),
            createdAt=timestamp,
            updatedAt=timestamp,
        )

        order_data = order.model_dump(by_alias=True)

        response = await service.save(
            entity=order_data,
            entity_class=Order.ENTITY_NAME,
            entity_version=str(Order.ENTITY_VERSION),
        )

        result = response.data.model_dump(by_alias=True)

        return (
            jsonify(
                {
                    "orderId": result.get("orderId"),
                    "orderNumber": result.get("orderNumber"),
                    "status": result.get("status"),
                }
            ),
            201,
        )

    except Exception as e:
        logger.exception("Error creating order: %s", str(e))
        return jsonify({"error": str(e)}), 500


@ui_order_bp.route("/<order_id>", methods=["GET"])
@tag(["order"])
@operation_id("get_order")
async def get_order(order_id: str) -> ResponseReturnValue:
    """Get order by ID"""
    try:
        service = get_entity_service()

        result = await service.get_by_id(
            entity_id=order_id,
            entity_class=Order.ENTITY_NAME,
            entity_version=str(Order.ENTITY_VERSION),
        )

        if not result:
            return jsonify({"error": "Order not found"}), 404

        order_data = result.data.model_dump(by_alias=True)
        return jsonify(order_data), 200

    except Exception as e:
        logger.exception("Error getting order %s: %s", order_id, str(e))
        return jsonify({"error": str(e)}), 500
