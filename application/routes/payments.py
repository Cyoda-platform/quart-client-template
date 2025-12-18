import logging
from typing import Any, Dict

from quart import Blueprint, jsonify, request
from quart.typing import ResponseReturnValue
from quart_schema import operation_id, tag, validate

from application.entity.payment.version_1.payment import Payment
from common.service.entity_service import SearchConditionRequest
from services.services import get_entity_service

logger = logging.getLogger(__name__)


class _ServiceProxy:
    def __getattr__(self, name: str) -> Any:
        return getattr(get_entity_service(), name)


service = _ServiceProxy()


def _to_entity_dict(data: Any) -> Dict[str, Any]:
    return data.model_dump(by_alias=True) if hasattr(data, "model_dump") else data


payments_bp = Blueprint("payments", __name__, url_prefix="/api/payments")


@payments_bp.route("", methods=["POST"])
@tag(["payments"])
@operation_id("create_payment")
@validate(
    request=Payment,
    responses={
        201: (Dict[str, Any], None),
        400: (Dict[str, str], None),
        500: (Dict[str, str], None),
    },
)
async def create_payment(data: Payment) -> ResponseReturnValue:
    try:
        entity_data = data.model_dump(by_alias=True)

        response = await service.save(
            entity=entity_data,
            entity_class=Payment.ENTITY_NAME,
            entity_version=str(Payment.ENTITY_VERSION),
        )

        logger.info("Created Payment with ID: %s", response.metadata.id)
        return _to_entity_dict(response.data), 201

    except ValueError as e:
        logger.warning("Validation error creating Payment: %s", str(e))
        return {"error": str(e), "code": "VALIDATION_ERROR"}, 400
    except Exception as e:
        logger.exception("Error creating Payment: %s", str(e))
        return {"error": str(e), "code": "INTERNAL_ERROR"}, 500


@payments_bp.route("/<entity_id>", methods=["GET"])
@tag(["payments"])
@operation_id("get_payment")
@validate(
    responses={
        200: (Dict[str, Any], None),
        404: (Dict[str, str], None),
        500: (Dict[str, str], None),
    }
)
async def get_payment(entity_id: str) -> ResponseReturnValue:
    try:
        if not entity_id or len(entity_id.strip()) == 0:
            return {"error": "Entity ID is required", "code": "INVALID_ID"}, 400

        response = await service.get_by_id(
            entity_id=entity_id,
            entity_class=Payment.ENTITY_NAME,
            entity_version=str(Payment.ENTITY_VERSION),
        )

        if not response:
            return {"error": "Payment not found", "code": "NOT_FOUND"}, 404

        return _to_entity_dict(response.data), 200

    except Exception as e:
        logger.exception("Error getting Payment %s: %s", entity_id, str(e))
        return {"error": str(e), "code": "INTERNAL_ERROR"}, 500


@payments_bp.route("", methods=["GET"])
@tag(["payments"])
@operation_id("list_payments")
@validate(
    responses={
        200: (Dict[str, Any], None),
        500: (Dict[str, str], None),
    }
)
async def list_payments() -> ResponseReturnValue:
    try:
        merchant_id = request.args.get("merchant_id")
        customer_id = request.args.get("customer_id")
        state = request.args.get("state")

        search_conditions: Dict[str, str] = {}
        if merchant_id:
            search_conditions["merchant_id"] = merchant_id
        if customer_id:
            search_conditions["customer_id"] = customer_id
        if state:
            search_conditions["state"] = state

        if search_conditions:
            builder = SearchConditionRequest.builder()
            for field, value in search_conditions.items():
                builder.equals(field, value)
            condition = builder.build()

            entities = await service.search(
                entity_class=Payment.ENTITY_NAME,
                condition=condition,
                entity_version=str(Payment.ENTITY_VERSION),
            )
        else:
            entities = await service.find_all(
                entity_class=Payment.ENTITY_NAME,
                entity_version=str(Payment.ENTITY_VERSION),
            )

        entity_list = [_to_entity_dict(r.data) for r in entities]
        return {"payments": entity_list, "total": len(entity_list)}, 200

    except Exception as e:
        logger.exception("Error listing Payments: %s", str(e))
        return {"error": str(e)}, 500


@payments_bp.route("/<entity_id>/capture", methods=["POST"])
@tag(["payments"])
@operation_id("capture_payment")
@validate(
    responses={
        200: (Dict[str, Any], None),
        404: (Dict[str, str], None),
        500: (Dict[str, str], None),
    }
)
async def capture_payment(entity_id: str) -> ResponseReturnValue:
    try:
        response = await service.get_by_id(
            entity_id=entity_id,
            entity_class=Payment.ENTITY_NAME,
            entity_version=str(Payment.ENTITY_VERSION),
        )

        if not response:
            return {"error": "Payment not found", "code": "NOT_FOUND"}, 404

        payment_data = _to_entity_dict(response.data)
        payment_data["capture_status"] = "captured"

        updated = await service.update(
            entity_id=entity_id,
            entity=payment_data,
            entity_class=Payment.ENTITY_NAME,
            entity_version=str(Payment.ENTITY_VERSION),
        )

        logger.info("Captured Payment %s", entity_id)
        return _to_entity_dict(updated.data), 200

    except Exception as e:
        logger.exception("Error capturing Payment %s: %s", entity_id, str(e))
        return {"error": str(e), "code": "INTERNAL_ERROR"}, 500


@payments_bp.route("/<entity_id>/refund", methods=["POST"])
@tag(["payments"])
@operation_id("refund_payment")
@validate(
    responses={
        200: (Dict[str, Any], None),
        404: (Dict[str, str], None),
        500: (Dict[str, str], None),
    }
)
async def refund_payment(entity_id: str) -> ResponseReturnValue:
    try:
        response = await service.get_by_id(
            entity_id=entity_id,
            entity_class=Payment.ENTITY_NAME,
            entity_version=str(Payment.ENTITY_VERSION),
        )

        if not response:
            return {"error": "Payment not found", "code": "NOT_FOUND"}, 404

        payment_data = _to_entity_dict(response.data)
        payment_data["capture_status"] = "refunded"

        updated = await service.update(
            entity_id=entity_id,
            entity=payment_data,
            entity_class=Payment.ENTITY_NAME,
            entity_version=str(Payment.ENTITY_VERSION),
        )

        logger.info("Refunded Payment %s", entity_id)
        return _to_entity_dict(updated.data), 200

    except Exception as e:
        logger.exception("Error refunding Payment %s: %s", entity_id, str(e))
        return {"error": str(e), "code": "INTERNAL_ERROR"}, 500
