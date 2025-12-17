from typing import Any, Dict

from quart import Blueprint, jsonify, request
from quart.typing import ResponseReturnValue
from quart_schema import operation_id, tag, validate

from application.entity.risk_limit.version_1.risk_limit import RiskLimit
from common.service.entity_service import SearchConditionRequest
from services.services import get_entity_service

risk_limits_bp = Blueprint("risk_limits", __name__, url_prefix="/api/risk-limits")


def _to_entity_dict(data: Any) -> Dict[str, Any]:
    return data.model_dump(by_alias=True) if hasattr(data, "model_dump") else data


@risk_limits_bp.route("", methods=["POST"])
@tag(["risk-limits"])
@operation_id("create_risk_limit")
@validate(
    request=RiskLimit,
    responses={
        200: (Dict[str, Any], None),
        201: (Dict[str, Any], None),
        400: (Dict[str, Any], None),
        500: (Dict[str, Any], None),
    },
)
async def create_risk_limit(data: RiskLimit) -> ResponseReturnValue:
    try:
        service = get_entity_service()
        entity_data = data.model_dump(by_alias=True)
        response = await service.save(
            entity=entity_data,
            entity_class=RiskLimit.ENTITY_NAME,
            entity_version=str(RiskLimit.ENTITY_VERSION),
        )
        return jsonify(_to_entity_dict(response.data)), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@risk_limits_bp.route("/<entity_id>", methods=["GET"])
@tag(["risk-limits"])
@operation_id("get_risk_limit")
async def get_risk_limit(entity_id: str) -> ResponseReturnValue:
    try:
        service = get_entity_service()
        response = await service.get_by_id(
            entity_id=entity_id,
            entity_class=RiskLimit.ENTITY_NAME,
            entity_version=str(RiskLimit.ENTITY_VERSION),
        )
        if not response:
            return jsonify({"error": "RiskLimit not found"}), 404
        return jsonify(_to_entity_dict(response.data)), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@risk_limits_bp.route("/<entity_id>", methods=["PUT"])
@tag(["risk-limits"])
@operation_id("update_risk_limit")
@validate(
    request=RiskLimit,
    responses={
        200: (Dict[str, Any], None),
        201: (Dict[str, Any], None),
        400: (Dict[str, Any], None),
        500: (Dict[str, Any], None),
    },
)
async def update_risk_limit(entity_id: str, data: RiskLimit) -> ResponseReturnValue:
    try:
        service = get_entity_service()
        transition = request.args.get("transition")
        entity_data = data.model_dump(by_alias=True)
        response = await service.update(
            entity_id=entity_id,
            entity=entity_data,
            entity_class=RiskLimit.ENTITY_NAME,
            transition=transition,
            entity_version=str(RiskLimit.ENTITY_VERSION),
        )
        return jsonify(_to_entity_dict(response.data)), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@risk_limits_bp.route("/<entity_id>", methods=["DELETE"])
@tag(["risk-limits"])
@operation_id("delete_risk_limit")
async def delete_risk_limit(entity_id: str) -> ResponseReturnValue:
    try:
        service = get_entity_service()
        await service.delete_by_id(
            entity_id=entity_id,
            entity_class=RiskLimit.ENTITY_NAME,
            entity_version=str(RiskLimit.ENTITY_VERSION),
        )
        return jsonify({"success": True, "entity_id": entity_id}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@risk_limits_bp.route("", methods=["GET"])
@tag(["risk-limits"])
@operation_id("list_risk_limits")
async def list_risk_limits() -> ResponseReturnValue:
    try:
        service = get_entity_service()
        args = request.args
        if args:
            builder = SearchConditionRequest.builder()
            for k, v in args.items():
                if k not in ["limit", "offset"]:
                    builder.equals(k, v)
            condition = builder.build()
                        results = await service.search(
                            RiskLimit.ENTITY_NAME, condition, str(RiskLimit.ENTITY_VERSION)
                        )
        else:
            results = await service.find_all(
                RiskLimit.ENTITY_NAME, str(RiskLimit.ENTITY_VERSION)
            )

        entities = [_to_entity_dict(r.data) for r in results]
        return jsonify({"entities": entities, "total": len(entities)}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
