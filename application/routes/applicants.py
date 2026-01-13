import logging
from typing import Any, Dict

from quart import Blueprint, request
from quart.typing import ResponseReturnValue
from quart_schema import operation_id, tag, validate

from application.entity.applicant.version_1.applicant import Applicant
from services.services import get_entity_service

logger = logging.getLogger(__name__)


class _ServiceProxy:
    def __getattr__(self, name: str) -> Any:
        return getattr(get_entity_service(), name)


service = _ServiceProxy()

def _to_entity_dict(data: Any) -> Dict[str, Any]:
    if data is None:
        raise ValueError("Cannot serialize None entity to dictionary")
    return data.model_dump(by_alias=True) if hasattr(data, "model_dump") else data


applicants_bp = Blueprint("applicants", __name__, url_prefix="/api/applicants")


@applicants_bp.route("", methods=["POST"])
@tag(["applicants"])
@operation_id("create_applicant")
@validate(responses={201: (None, None), 400: (None, None), 500: (None, None)})
async def create_applicant(data: Applicant) -> ResponseReturnValue:
    try:
        entity_data = data.model_dump(by_alias=True)
        response = await service.save(
            entity=entity_data,
            entity_class=Applicant.ENTITY_NAME,
            entity_version=str(Applicant.ENTITY_VERSION),
        )
        logger.info("Created Applicant with ID: %s", response.metadata.id)
        return _to_entity_dict(response.data), 201
    except ValueError as e:
        logger.warning("Validation error: %s", str(e))
        return {"error": str(e)}, 400
    except Exception as e:
        logger.exception("Error creating applicant: %s", str(e))
        return {"error": str(e)}, 500


@applicants_bp.route("/<entity_id>", methods=["GET"])
@tag(["applicants"])
@operation_id("get_applicant")
@validate(responses={200: (None, None), 404: (None, None), 500: (None, None)})
async def get_applicant(entity_id: str) -> ResponseReturnValue:
    try:
        if not entity_id or len(entity_id.strip()) == 0:
            return {"error": "Entity ID is required"}, 400

        response = await service.get_by_id(
            entity_id=entity_id,
            entity_class=Applicant.ENTITY_NAME,
            entity_version=str(Applicant.ENTITY_VERSION),
        )

        if not response:
            return {"error": "Applicant not found"}, 404

        return _to_entity_dict(response.data), 200
    except Exception as e:
        logger.exception("Error getting applicant: %s", str(e))
        return {"error": str(e)}, 500


@applicants_bp.route("/<entity_id>", methods=["PUT"])
@tag(["applicants"])
@operation_id("update_applicant")
@validate(responses={200: (None, None), 404: (None, None), 500: (None, None)})
async def update_applicant(entity_id: str, data: Applicant) -> ResponseReturnValue:
    try:
        entity_data = data.model_dump(by_alias=True)
        response = await service.update(
            entity_id=entity_id,
            entity=entity_data,
            entity_class=Applicant.ENTITY_NAME,
            entity_version=str(Applicant.ENTITY_VERSION),
        )

        if not response:
            return {"error": "Applicant not found"}, 404

        return _to_entity_dict(response.data), 200
    except Exception as e:
        logger.exception("Error updating applicant: %s", str(e))
        return {"error": str(e)}, 500


@applicants_bp.route("/<entity_id>", methods=["DELETE"])
@tag(["applicants"])
@operation_id("delete_applicant")
@validate(responses={200: (None, None), 404: (None, None), 500: (None, None)})
async def delete_applicant(entity_id: str) -> ResponseReturnValue:
    try:
        success = await service.delete(
            entity_id=entity_id,
            entity_class=Applicant.ENTITY_NAME,
            entity_version=str(Applicant.ENTITY_VERSION),
        )

        if not success:
            return {"error": "Applicant not found"}, 404

        return {"message": "Applicant deleted"}, 200
    except Exception as e:
        logger.exception("Error deleting applicant: %s", str(e))
        return {"error": str(e)}, 500


@applicants_bp.route("/<entity_id>/transitions", methods=["GET"])
@tag(["applicants"])
@operation_id("get_applicant_transitions")
@validate(responses={200: (None, None), 404: (None, None), 500: (None, None)})
async def get_transitions(entity_id: str) -> ResponseReturnValue:
    try:
        response = await service.get_available_transitions(
            entity_id=entity_id,
            entity_class=Applicant.ENTITY_NAME,
            entity_version=str(Applicant.ENTITY_VERSION),
        )

        if not response:
            return {"error": "Applicant not found"}, 404

        return {"transitions": response}, 200
    except Exception as e:
        logger.exception("Error getting transitions: %s", str(e))
        return {"error": str(e)}, 500


@applicants_bp.route("/<entity_id>/transition", methods=["POST"])
@tag(["applicants"])
@operation_id("trigger_applicant_transition")
@validate(responses={200: (None, None), 404: (None, None), 500: (None, None)})
async def trigger_transition(entity_id: str) -> ResponseReturnValue:
    try:
        data = await request.get_json()
        transition_name = data.get("transition_name")

        if not transition_name:
            return {"error": "transition_name is required"}, 400

        response = await service.execute_transition(
            entity_id=entity_id,
            transition=transition_name,
            entity_class=Applicant.ENTITY_NAME,
            entity_version=str(Applicant.ENTITY_VERSION),
        )

        return _to_entity_dict(response.data), 200
    except Exception as e:
        logger.exception("Error triggering transition: %s", str(e))
        return {"error": str(e)}, 500
