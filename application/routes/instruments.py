from typing import Any, Dict

from quart import Blueprint, jsonify, request
from quart.typing import ResponseReturnValue
from quart_schema import operation_id, tag, validate

from common.service.entity_service import SearchConditionRequest
from services.services import get_entity_service
from application.entity.instrument.version_1.instrument import Instrument

instruments_bp = Blueprint("instruments", __name__, url_prefix="/api/instruments")


def _to_entity_dict(data: Any) -> Dict[str, Any]:
    return data.model_dump(by_alias=True) if hasattr(data, "model_dump") else data


@instruments_bp.route("", methods=["POST"])
@tag(["instruments"])
@operation_id("create_instrument")
@validate(request=Instrument)
async def create_instrument(data: Instrument) -> ResponseReturnValue:
    try:
        service = get_entity_service()
        entity_data = data.model_dump(by_alias=True)
        response = await service.save(
            entity=entity_data,
            entity_class=Instrument.ENTITY_NAME,
            entity_version=str(Instrument.ENTITY_VERSION),
        )
        return jsonify(_to_entity_dict(response.data)), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@instruments_bp.route("/<entity_id>", methods=["GET"])
@tag(["instruments"])
@operation_id("get_instrument")
async def get_instrument(entity_id: str) -> ResponseReturnValue:
    try:
        service = get_entity_service()
        response = await service.get_by_id(
            entity_id=entity_id,
            entity_class=Instrument.ENTITY_NAME,
            entity_version=str(Instrument.ENTITY_VERSION),
        )
        if not response:
            return jsonify({"error": "Instrument not found"}), 404
        return jsonify(_to_entity_dict(response.data)), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@instruments_bp.route("/<entity_id>", methods=["PUT"])
@tag(["instruments"])
@operation_id("update_instrument")
@validate(request=Instrument)
async def update_instrument(entity_id: str, data: Instrument) -> ResponseReturnValue:
    try:
        service = get_entity_service()
        transition = request.args.get("transition")
        entity_data = data.model_dump(by_alias=True)
        response = await service.update(
            entity_id=entity_id,
            entity=entity_data,
            entity_class=Instrument.ENTITY_NAME,
            transition=transition,
            entity_version=str(Instrument.ENTITY_VERSION),
        )
        return jsonify(_to_entity_dict(response.data)), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@instruments_bp.route("/<entity_id>", methods=["DELETE"])
@tag(["instruments"])
@operation_id("delete_instrument")
async def delete_instrument(entity_id: str) -> ResponseReturnValue:
    try:
        service = get_entity_service()
        await service.delete_by_id(
            entity_id=entity_id,
            entity_class=Instrument.ENTITY_NAME,
            entity_version=str(Instrument.ENTITY_VERSION),
        )
        return jsonify({"success": True, "entity_id": entity_id}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@instruments_bp.route("", methods=["GET"])
@tag(["instruments"])
@operation_id("list_instruments")
async def list_instruments() -> ResponseReturnValue:
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
                Instrument.ENTITY_NAME, condition, str(Instrument.ENTITY_VERSION)
            )
        else:
            results = await service.find_all(
                Instrument.ENTITY_NAME, str(Instrument.ENTITY_VERSION)
            )

        entities = [_to_entity_dict(r.data) for r in results]
        return jsonify({"entities": entities, "total": len(entities)}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
