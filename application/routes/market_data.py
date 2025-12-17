import logging
from typing import Any, Dict

from quart import Blueprint, jsonify, request
from quart.typing import ResponseReturnValue
from quart_schema import operation_id, tag, validate

from application.entity.market_data.version_1.market_data import MarketData
from services.services import get_entity_service

logger = logging.getLogger(__name__)


class _ServiceProxy:
    def __getattr__(self, name: str) -> Any:
        return getattr(get_entity_service(), name)


service = _ServiceProxy()


def _to_entity_dict(data: Any) -> Dict[str, Any]:
    return data.model_dump(by_alias=True) if hasattr(data, "model_dump") else data


market_data_bp = Blueprint("market_data", __name__, url_prefix="/api/market-data")


@market_data_bp.route("", methods=["POST"])
@tag(["market-data"])
@operation_id("create_market_data")
@validate(
    request=MarketData,
    responses={
        201: (Dict[str, Any], None),
        400: (Dict[str, str], None),
        500: (Dict[str, str], None),
    },
)
async def create_market_data(data: MarketData) -> ResponseReturnValue:
    """Create a new MarketData"""
    try:
        entity_data = data.model_dump(by_alias=True)
        response = await service.save(
            entity=entity_data,
            entity_class=MarketData.ENTITY_NAME,
            entity_version=str(MarketData.ENTITY_VERSION),
        )
        logger.info("Created MarketData with ID: %s", response.metadata.id)
        return _to_entity_dict(response.data), 201
    except ValueError as e:
        logger.warning("Validation error creating MarketData: %s", str(e))
        return {"error": str(e), "code": "VALIDATION_ERROR"}, 400
    except Exception as e:
        logger.exception("Error creating MarketData: %s", str(e))
        return {"error": str(e), "code": "INTERNAL_ERROR"}, 500


@market_data_bp.route("/<entity_id>", methods=["GET"])
@tag(["market-data"])
@operation_id("get_market_data")
@validate(
    responses={
        200: (Dict[str, Any], None),
        404: (Dict[str, str], None),
        500: (Dict[str, str], None),
    }
)
async def get_market_data(entity_id: str) -> ResponseReturnValue:
    """Get MarketData by ID"""
    try:
        if not entity_id or len(entity_id.strip()) == 0:
            return {"error": "Entity ID is required", "code": "INVALID_ID"}, 400

        response = await service.get_by_id(
            entity_id=entity_id,
            entity_class=MarketData.ENTITY_NAME,
            entity_version=str(MarketData.ENTITY_VERSION),
        )

        if not response:
            return {"error": "MarketData not found", "code": "NOT_FOUND"}, 404

        return _to_entity_dict(response.data), 200
    except Exception as e:
        logger.exception("Error getting MarketData %s: %s", entity_id, str(e))
        return {"error": str(e), "code": "INTERNAL_ERROR"}, 500


@market_data_bp.route("", methods=["GET"])
@tag(["market-data"])
@operation_id("list_market_data")
@validate(
    responses={
        200: (Dict[str, Any], None),
        500: (Dict[str, str], None),
    }
)
async def list_market_data() -> ResponseReturnValue:
    """List all MarketData"""
    try:
        entities = await service.find_all(
            entity_class=MarketData.ENTITY_NAME,
            entity_version=str(MarketData.ENTITY_VERSION),
        )
        entity_list = [_to_entity_dict(r.data) for r in entities]
        return jsonify({"entities": entity_list, "total": len(entity_list)}), 200
    except Exception as e:
        logger.exception("Error listing MarketData: %s", str(e))
        return jsonify({"error": str(e)}), 500


@market_data_bp.route("/<entity_id>", methods=["PUT"])
@tag(["market-data"])
@operation_id("update_market_data")
@validate(
    request=MarketData,
    responses={
        200: (Dict[str, Any], None),
        404: (Dict[str, str], None),
        500: (Dict[str, str], None),
    },
)
async def update_market_data(entity_id: str, data: MarketData) -> ResponseReturnValue:
    """Update MarketData"""
    try:
        if not entity_id or len(entity_id.strip()) == 0:
            return {"error": "Entity ID is required", "code": "INVALID_ID"}, 400

        entity_data: Dict[str, Any] = data.model_dump(by_alias=True)
        response = await service.update(
            entity_id=entity_id,
            entity=entity_data,
            entity_class=MarketData.ENTITY_NAME,
            entity_version=str(MarketData.ENTITY_VERSION),
        )

        logger.info("Updated MarketData %s", entity_id)
        return jsonify(_to_entity_dict(response.data)), 200
    except Exception as e:
        logger.exception("Error updating MarketData %s: %s", entity_id, str(e))
        return jsonify({"error": str(e), "code": "INTERNAL_ERROR"}), 500


@market_data_bp.route("/<entity_id>", methods=["DELETE"])
@tag(["market-data"])
@operation_id("delete_market_data")
@validate(
    responses={
        200: (Dict[str, Any], None),
        404: (Dict[str, str], None),
        500: (Dict[str, str], None),
    }
)
async def delete_market_data(entity_id: str) -> ResponseReturnValue:
    """Delete MarketData"""
    try:
        if not entity_id or len(entity_id.strip()) == 0:
            return {"error": "Entity ID is required", "code": "INVALID_ID"}, 400

        await service.delete_by_id(
            entity_id=entity_id,
            entity_class=MarketData.ENTITY_NAME,
            entity_version=str(MarketData.ENTITY_VERSION),
        )

        logger.info("Deleted MarketData %s", entity_id)
        return {"success": True, "message": "MarketData deleted successfully"}, 200
    except Exception as e:
        logger.exception("Error deleting MarketData %s: %s", entity_id, str(e))
        return {"error": str(e), "code": "INTERNAL_ERROR"}, 500


@market_data_bp.route("/<entity_id>/transitions", methods=["POST"])
@tag(["market-data"])
@operation_id("trigger_market_data_transition")
@validate(
    responses={
        200: (Dict[str, Any], None),
        500: (Dict[str, str], None),
    }
)
async def trigger_market_data_transition(entity_id: str) -> ResponseReturnValue:
    """Trigger workflow transition for MarketData"""
    try:
        data = await request.get_json()
        transition_name = data.get("transition_name")

        if not transition_name:
            return {"error": "transition_name is required"}, 400

        response = await service.execute_transition(
            entity_id=entity_id,
            transition=transition_name,
            entity_class=MarketData.ENTITY_NAME,
            entity_version=str(MarketData.ENTITY_VERSION),
        )

        logger.info(
            "Executed transition '%s' on MarketData %s", transition_name, entity_id
        )
        return (
            jsonify({"id": response.metadata.id, "state": response.metadata.state}),
            200,
        )
    except Exception as e:
        logger.exception(
            "Error executing transition on MarketData %s: %s", entity_id, str(e)
        )
        return jsonify({"error": str(e)}), 500
