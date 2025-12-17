from typing import Any, Dict

from quart import Blueprint, jsonify, request
from quart.typing import ResponseReturnValue
from quart_schema import operation_id, tag, validate

from application.entity.position.version_1.position import Position
from common.service.entity_service import SearchConditionRequest
from services.services import get_entity_service

positions_bp = Blueprint("positions", __name__, url_prefix="/api/positions")


def _to_entity_dict(data: Any) -> Dict[str, Any]:
    return data.model_dump(by_alias=True) if hasattr(data, "model_dump") else data


@positions_bp.route("", methods=["POST"])
@tag(["positions"])
@operation_id("create_position")
@validate(
    request=Position,
    responses={
        200: (Dict[str, Any], None),
        201: (Dict[str, Any], None),
        400: (Dict[str, Any], None),
        500: (Dict[str, Any], None),
    },
)
async def create_position(data: Position) -> ResponseReturnValue:
    try:
        service = get_entity_service()
        entity_data = data.model_dump(by_alias=True)
        response = await service.save(
            entity=entity_data,
            entity_class=Position.ENTITY_NAME,
            entity_version=str(Position.ENTITY_VERSION),
        )
        return jsonify(_to_entity_dict(response.data)), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@positions_bp.route("/<entity_id>", methods=["GET"])
@tag(["positions"])
@operation_id("get_position")
async def get_position(entity_id: str) -> ResponseReturnValue:
    try:
        service = get_entity_service()
        response = await service.get_by_id(
            entity_id=entity_id,
            entity_class=Position.ENTITY_NAME,
            entity_version=str(Position.ENTITY_VERSION),
        )
        if not response:
            return jsonify({"error": "Position not found"}), 404
        return jsonify(_to_entity_dict(response.data)), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@positions_bp.route("/<entity_id>", methods=["PUT"])
@tag(["positions"])
@operation_id("update_position")
@validate(
    request=Position,
    responses={
        200: (Dict[str, Any], None),
        201: (Dict[str, Any], None),
        400: (Dict[str, Any], None),
        500: (Dict[str, Any], None),
    },
)
async def update_position(entity_id: str, data: Position) -> ResponseReturnValue:
    try:
        service = get_entity_service()
        transition = request.args.get("transition")
        entity_data = data.model_dump(by_alias=True)
        response = await service.update(
            entity_id=entity_id,
            entity=entity_data,
            entity_class=Position.ENTITY_NAME,
            transition=transition,
            entity_version=str(Position.ENTITY_VERSION),
        )
        return jsonify(_to_entity_dict(response.data)), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@positions_bp.route("/<entity_id>", methods=["DELETE"])
@tag(["positions"])
@operation_id("delete_position")
async def delete_position(entity_id: str) -> ResponseReturnValue:
    try:
        service = get_entity_service()
        await service.delete_by_id(
            entity_id=entity_id,
            entity_class=Position.ENTITY_NAME,
            entity_version=str(Position.ENTITY_VERSION),
        )
        return jsonify({"success": True, "entity_id": entity_id}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@positions_bp.route("", methods=["GET"])
@tag(["positions"])
@operation_id("list_positions")
async def list_positions() -> ResponseReturnValue:
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
                Position.ENTITY_NAME, condition, str(Position.ENTITY_VERSION)
            )
        else:
            results = await service.find_all(
                Position.ENTITY_NAME, str(Position.ENTITY_VERSION)
            )

        entities = [_to_entity_dict(r.data) for r in results]
        return jsonify({"entities": entities, "total": len(entities)}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
