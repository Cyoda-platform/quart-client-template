import logging
from datetime import datetime, timezone
from uuid import uuid4

from quart import Blueprint, jsonify, request
from quart.typing import ResponseReturnValue
from quart_schema import operation_id, tag

from application.entity.payment import Payment
from services.services import get_entity_service

logger = logging.getLogger(__name__)

ui_payment_bp = Blueprint("ui_payment", __name__, url_prefix="/ui/payment")


def _get_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


@ui_payment_bp.route("/start", methods=["POST"])
@tag(["payment"])
@operation_id("start_payment")
async def start_payment() -> ResponseReturnValue:
    """Start dummy payment (auto-PAID after ~3s)"""
    try:
        data = await request.get_json()
        cart_id = data.get("cartId")
        amount = data.get("amount", 0.0)

        if not cart_id:
            return jsonify({"error": "cartId is required"}), 400

        service = get_entity_service()

        timestamp = _get_timestamp()
        payment_id = str(uuid4())

        payment = Payment(
            paymentId=payment_id,
            cartId=cart_id,
            amount=amount,
            status="INITIATED",
            provider="DUMMY",
            createdAt=timestamp,
            updatedAt=timestamp,
        )

        payment_data = payment.model_dump(by_alias=True)

        response = await service.save(
            entity=payment_data,
            entity_class=Payment.ENTITY_NAME,
            entity_version=str(Payment.ENTITY_VERSION),
        )

        result = response.data.model_dump(by_alias=True)
        return jsonify({"paymentId": result.get("paymentId")}), 201

    except Exception as e:
        logger.exception("Error starting payment: %s", str(e))
        return jsonify({"error": str(e)}), 500


@ui_payment_bp.route("/<payment_id>", methods=["GET"])
@tag(["payment"])
@operation_id("get_payment_status")
async def get_payment_status(payment_id: str) -> ResponseReturnValue:
    """Get payment status"""
    try:
        service = get_entity_service()

        result = await service.get_by_id(
            entity_id=payment_id,
            entity_class=Payment.ENTITY_NAME,
            entity_version=str(Payment.ENTITY_VERSION),
        )

        if not result:
            return jsonify({"error": "Payment not found"}), 404

        payment_data = result.data.model_dump(by_alias=True)
        return jsonify(payment_data), 200

    except Exception as e:
        logger.exception("Error getting payment %s: %s", payment_id, str(e))
        return jsonify({"error": str(e)}), 500
