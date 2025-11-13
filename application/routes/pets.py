"""
Pet Routes for Cyoda Client Application.

Manages all Pet-related API endpoints including CRUD operations
and workflow transitions for downloading pet data from Petstore API.
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from quart import Blueprint, jsonify, request
from quart.typing import ResponseReturnValue
from quart_schema import operation_id, tag, validate

from application.entity.pet import Pet
from services.services import get_entity_service

logger = logging.getLogger(__name__)


class _ServiceProxy:
    def __getattr__(self, name: str) -> Any:
        return getattr(get_entity_service(), name)


service = _ServiceProxy()


def _to_entity_dict(data: Any) -> Dict[str, Any]:
    return data.model_dump(by_alias=True) if hasattr(data, "model_dump") else data


pets_bp = Blueprint("pets", __name__, url_prefix="/api/pets")


@pets_bp.route("", methods=["POST"])
@tag(["pets"])
@operation_id("create_pet")
@validate(
    request=Pet,
    responses={
        201: (Dict[str, Any], None),
        400: (Dict[str, str], None),
        500: (Dict[str, str], None),
    },
)
async def create_pet(data: Pet) -> ResponseReturnValue:
    """Create a new Pet"""
    try:
        entity_data = data.model_dump(by_alias=True)

        response = await service.save(
            entity=entity_data,
            entity_class=Pet.ENTITY_NAME,
            entity_version=str(Pet.ENTITY_VERSION),
        )

        logger.info("Created Pet with ID: %s", response.metadata.id)
        return _to_entity_dict(response.data), 201

    except ValueError as e:
        logger.warning("Validation error creating Pet: %s", str(e))
        return {"error": str(e), "code": "VALIDATION_ERROR"}, 400
    except Exception as e:
        logger.exception("Error creating Pet: %s", str(e))
        return {"error": str(e), "code": "INTERNAL_ERROR"}, 500


@pets_bp.route("/<entity_id>", methods=["GET"])
@tag(["pets"])
@operation_id("get_pet")
@validate(
    responses={
        200: (Dict[str, Any], None),
        404: (Dict[str, str], None),
        400: (Dict[str, str], None),
        500: (Dict[str, str], None),
    }
)
async def get_pet(entity_id: str) -> ResponseReturnValue:
    """Get Pet by ID"""
    try:
        if not entity_id or len(entity_id.strip()) == 0:
            return {"error": "Entity ID is required", "code": "INVALID_ID"}, 400

        response = await service.get_by_id(
            entity_id=entity_id,
            entity_class=Pet.ENTITY_NAME,
            entity_version=str(Pet.ENTITY_VERSION),
        )

        if not response:
            return {"error": "Pet not found", "code": "NOT_FOUND"}, 404

        return _to_entity_dict(response.data), 200

    except ValueError as e:
        logger.warning("Invalid entity ID %s: %s", entity_id, str(e))
        return {"error": str(e), "code": "INVALID_ID"}, 400
    except Exception as e:
        logger.exception("Error getting Pet %s: %s", entity_id, str(e))
        return {"error": str(e), "code": "INTERNAL_ERROR"}, 500


@pets_bp.route("", methods=["GET"])
@tag(["pets"])
@operation_id("list_pets")
@validate(
    responses={
        200: (Dict[str, Any], None),
        500: (Dict[str, str], None),
    }
)
async def list_pets() -> ResponseReturnValue:
    """List all Pets"""
    try:
        entities = await service.find_all(
            entity_class=Pet.ENTITY_NAME,
            entity_version=str(Pet.ENTITY_VERSION),
        )

        entity_list = [_to_entity_dict(r.data) for r in entities]
        return jsonify({"entities": entity_list, "total": len(entity_list)}), 200

    except Exception as e:
        logger.exception("Error listing Pets: %s", str(e))
        return jsonify({"error": str(e)}), 500


@pets_bp.route("/<entity_id>", methods=["PUT"])
@tag(["pets"])
@operation_id("update_pet")
@validate(
    request=Pet,
    responses={
        200: (Dict[str, Any], None),
        404: (Dict[str, str], None),
        400: (Dict[str, str], None),
        500: (Dict[str, str], None),
    },
)
async def update_pet(entity_id: str, data: Pet) -> ResponseReturnValue:
    """Update Pet"""
    try:
        if not entity_id or len(entity_id.strip()) == 0:
            return {"error": "Entity ID is required", "code": "INVALID_ID"}, 400

        entity_data: Dict[str, Any] = data.model_dump(by_alias=True)

        response = await service.update(
            entity_id=entity_id,
            entity=entity_data,
            entity_class=Pet.ENTITY_NAME,
            entity_version=str(Pet.ENTITY_VERSION),
        )

        logger.info("Updated Pet %s", entity_id)
        return jsonify(_to_entity_dict(response.data)), 200

    except ValueError as e:
        logger.warning("Validation error updating Pet %s: %s", entity_id, str(e))
        return jsonify({"error": str(e), "code": "VALIDATION_ERROR"}), 400
    except Exception as e:
        logger.exception("Error updating Pet %s: %s", entity_id, str(e))
        return jsonify({"error": str(e), "code": "INTERNAL_ERROR"}), 500


@pets_bp.route("/<entity_id>", methods=["DELETE"])
@tag(["pets"])
@operation_id("delete_pet")
@validate(
    responses={
        200: (Dict[str, Any], None),
        404: (Dict[str, str], None),
        400: (Dict[str, str], None),
        500: (Dict[str, str], None),
    }
)
async def delete_pet(entity_id: str) -> ResponseReturnValue:
    """Delete Pet"""
    try:
        if not entity_id or len(entity_id.strip()) == 0:
            return {"error": "Entity ID is required", "code": "INVALID_ID"}, 400

        await service.delete_by_id(
            entity_id=entity_id,
            entity_class=Pet.ENTITY_NAME,
            entity_version=str(Pet.ENTITY_VERSION),
        )

        logger.info("Deleted Pet %s", entity_id)
        return {"success": True, "message": "Pet deleted successfully"}, 200

    except ValueError as e:
        logger.warning("Invalid entity ID %s: %s", entity_id, str(e))
        return {"error": str(e), "code": "INVALID_ID"}, 400
    except Exception as e:
        logger.exception("Error deleting Pet %s: %s", entity_id, str(e))
        return {"error": str(e), "code": "INTERNAL_ERROR"}, 500


@pets_bp.route("/<entity_id>/transitions", methods=["GET"])
@tag(["pets"])
@operation_id("get_pet_transitions")
@validate(
    responses={
        200: (Dict[str, Any], None),
        404: (Dict[str, str], None),
        500: (Dict[str, str], None),
    }
)
async def get_pet_transitions(entity_id: str) -> ResponseReturnValue:
    """Get available workflow transitions for Pet"""
    try:
        transitions = await service.get_transitions(
            entity_id=entity_id,
            entity_class=Pet.ENTITY_NAME,
            entity_version=str(Pet.ENTITY_VERSION),
        )

        return (
            jsonify(
                {
                    "entity_id": entity_id,
                    "available_transitions": transitions,
                }
            ),
            200,
        )

    except Exception as e:
        logger.exception("Error getting transitions for Pet %s: %s", entity_id, str(e))
        return jsonify({"error": str(e)}), 500


@pets_bp.route("/<entity_id>/transitions", methods=["POST"])
@tag(["pets"])
@operation_id("trigger_pet_transition")
@validate(
    responses={
        200: (Dict[str, Any], None),
        404: (Dict[str, str], None),
        400: (Dict[str, str], None),
        500: (Dict[str, str], None),
    },
)
async def trigger_pet_transition(entity_id: str) -> ResponseReturnValue:
    """Trigger a workflow transition for Pet"""
    try:
        transition_name = request.args.get("transition")
        if not transition_name:
            return {"error": "transition query parameter required"}, 400

        response = await service.execute_transition(
            entity_id=entity_id,
            transition=transition_name,
            entity_class=Pet.ENTITY_NAME,
            entity_version=str(Pet.ENTITY_VERSION),
        )

        logger.info(
            "Executed transition '%s' on Pet %s",
            transition_name,
            entity_id,
        )

        return (
            jsonify(
                {
                    "id": response.metadata.id,
                    "message": "Transition executed successfully",
                    "newState": response.metadata.state,
                }
            ),
            200,
        )

    except Exception as e:
        logger.exception("Error executing transition on Pet %s: %s", entity_id, str(e))
        return jsonify({"error": str(e)}), 500
