import logging
from typing import Any, Dict

from quart import Blueprint, jsonify, request
from quart.typing import ResponseReturnValue
from quart_schema import operation_id, tag, validate

from application.entity.subscription.version_1.subscription import Subscription
from common.service.entity_service import SearchConditionRequest
from services.services import get_entity_service

logger = logging.getLogger(__name__)


class _ServiceProxy:
    def __getattr__(self, name: str) -> Any:
        return getattr(get_entity_service(), name)


service = _ServiceProxy()


def _to_entity_dict(data: Any) -> Dict[str, Any]:
    return data.model_dump(by_alias=True) if hasattr(data, "model_dump") else data


subscriptions_bp = Blueprint("subscriptions", __name__, url_prefix="/api/subscriptions")


@subscriptions_bp.route("", methods=["POST"])
@tag(["subscriptions"])
@operation_id("create_subscription")
@validate(
    request=Subscription,
    responses={
        201: (Dict[str, Any], None),
        400: (Dict[str, str], None),
        500: (Dict[str, str], None),
    },
)
async def create_subscription(data: Subscription) -> ResponseReturnValue:
    try:
        entity_data = data.model_dump(by_alias=True)

        response = await service.save(
            entity=entity_data,
            entity_class=Subscription.ENTITY_NAME,
            entity_version=str(Subscription.ENTITY_VERSION),
        )

        logger.info("Created Subscription with ID: %s", response.metadata.id)
        return _to_entity_dict(response.data), 201

    except ValueError as e:
        logger.warning("Validation error creating Subscription: %s", str(e))
        return {"error": str(e), "code": "VALIDATION_ERROR"}, 400
    except Exception as e:
        logger.exception("Error creating Subscription: %s", str(e))
        return {"error": str(e), "code": "INTERNAL_ERROR"}, 500


@subscriptions_bp.route("/<entity_id>", methods=["GET"])
@tag(["subscriptions"])
@operation_id("get_subscription")
@validate(
    responses={
        200: (Dict[str, Any], None),
        404: (Dict[str, str], None),
        500: (Dict[str, str], None),
    }
)
async def get_subscription(entity_id: str) -> ResponseReturnValue:
    try:
        if not entity_id or len(entity_id.strip()) == 0:
            return {"error": "Entity ID is required", "code": "INVALID_ID"}, 400

        response = await service.get_by_id(
            entity_id=entity_id,
            entity_class=Subscription.ENTITY_NAME,
            entity_version=str(Subscription.ENTITY_VERSION),
        )

        if not response:
            return {"error": "Subscription not found", "code": "NOT_FOUND"}, 404

        return _to_entity_dict(response.data), 200

    except Exception as e:
        logger.exception("Error getting Subscription %s: %s", entity_id, str(e))
        return {"error": str(e), "code": "INTERNAL_ERROR"}, 500


@subscriptions_bp.route("", methods=["GET"])
@tag(["subscriptions"])
@operation_id("list_subscriptions")
@validate(
    responses={
        200: (Dict[str, Any], None),
        500: (Dict[str, str], None),
    }
)
async def list_subscriptions() -> ResponseReturnValue:
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
                entity_class=Subscription.ENTITY_NAME,
                condition=condition,
                entity_version=str(Subscription.ENTITY_VERSION),
            )
        else:
            entities = await service.find_all(
                entity_class=Subscription.ENTITY_NAME,
                entity_version=str(Subscription.ENTITY_VERSION),
            )

        entity_list = [_to_entity_dict(r.data) for r in entities]
        return {"subscriptions": entity_list, "total": len(entity_list)}, 200

    except Exception as e:
        logger.exception("Error listing Subscriptions: %s", str(e))
        return {"error": str(e)}, 500


@subscriptions_bp.route("/<entity_id>/cancel", methods=["POST"])
@tag(["subscriptions"])
@operation_id("cancel_subscription")
@validate(
    responses={
        200: (Dict[str, Any], None),
        404: (Dict[str, str], None),
        500: (Dict[str, str], None),
    }
)
async def cancel_subscription(entity_id: str) -> ResponseReturnValue:
    try:
        response = await service.get_by_id(
            entity_id=entity_id,
            entity_class=Subscription.ENTITY_NAME,
            entity_version=str(Subscription.ENTITY_VERSION),
        )

        if not response:
            return {"error": "Subscription not found", "code": "NOT_FOUND"}, 404

        updated = await service.execute_transition(
            entity_id=entity_id,
            transition="cancel",
            entity_class=Subscription.ENTITY_NAME,
            entity_version=str(Subscription.ENTITY_VERSION),
        )

        logger.info("Cancelled Subscription %s", entity_id)
        return _to_entity_dict(updated.data), 200

    except Exception as e:
        logger.exception("Error cancelling Subscription %s: %s", entity_id, str(e))
        return {"error": str(e), "code": "INTERNAL_ERROR"}, 500
