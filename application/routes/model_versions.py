import logging
from typing import Any, Dict

from quart import Blueprint, request
from quart.typing import ResponseReturnValue
from quart_schema import operation_id, tag, validate

from application.entity.model_version.version_1.model_version import ModelVersion
from common.utils.serialization import safe_serialize
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


model_versions_bp = Blueprint(
    "model_versions", __name__, url_prefix="/api/model-versions"
)


@model_versions_bp.route("", methods=["POST"])
@tag(["model-versions"])
@operation_id("create_model_version")
@validate(responses={201: (dict, None), 400: (dict, None), 500: (dict, None)})
async def create_model_version(data: ModelVersion) -> ResponseReturnValue:
    try:
        if data is None:
            logger.warning("Create model version called with None payload")
            return {"error": "Request body is required"}, 400

        entity_data = data.model_dump(by_alias=True)
        response = await service.save(
            entity=entity_data,
            entity_class=ModelVersion.ENTITY_NAME,
            entity_version=str(ModelVersion.ENTITY_VERSION),
        )
        logger.info("Created ModelVersion with ID: %s", response.metadata.id)
        return _to_entity_dict(response.data), 201
    except ValueError as e:
        logger.warning("Validation error: %s", str(e))
        return {"error": str(e)}, 400
    except Exception as e:
        logger.exception("Error creating model version: %s", str(e))
        return {"error": str(e)}, 500


@model_versions_bp.route("/<entity_id>", methods=["GET"])
@tag(["model-versions"])
@operation_id("get_model_version")
@validate(responses={200: (dict, None), 404: (dict, None), 500: (dict, None)})
async def get_model_version(entity_id: str) -> ResponseReturnValue:
    try:
        if not entity_id or len(entity_id.strip()) == 0:
            return {"error": "Entity ID is required"}, 400

        response = await service.get_by_id(
            entity_id=entity_id,
            entity_class=ModelVersion.ENTITY_NAME,
            entity_version=str(ModelVersion.ENTITY_VERSION),
        )

        if not response:
            return {"error": "ModelVersion not found"}, 404

        return safe_serialize(response.data)
    except Exception as e:
        logger.exception("Error getting model version: %s", str(e))
        return {"error": str(e)}, 500


@model_versions_bp.route("/<entity_id>", methods=["PUT"])
@tag(["model-versions"])
@operation_id("update_model_version")
@validate(responses={200: (dict, None), 404: (dict, None), 500: (dict, None)})
async def update_model_version(
    entity_id: str, data: ModelVersion
) -> ResponseReturnValue:
    try:
        if data is None:
            logger.warning("Update model version called with None payload")
            return {"error": "Request body is required"}, 400

        entity_data = data.model_dump(by_alias=True)
        response = await service.update(
            entity_id=entity_id,
            entity=entity_data,
            entity_class=ModelVersion.ENTITY_NAME,
            entity_version=str(ModelVersion.ENTITY_VERSION),
        )

        if not response:
            return {"error": "ModelVersion not found"}, 404

        return _to_entity_dict(response.data), 200
    except Exception as e:
        logger.exception("Error updating model version: %s", str(e))
        return {"error": str(e)}, 500


@model_versions_bp.route("/<entity_id>/transition", methods=["POST"])
@tag(["model-versions"])
@operation_id("trigger_model_version_transition")
@validate(responses={200: (dict, None), 404: (dict, None), 500: (dict, None)})
async def trigger_transition(entity_id: str) -> ResponseReturnValue:
    try:
        data = await request.get_json()
        transition_name = data.get("transition_name")

        if not transition_name:
            return {"error": "transition_name is required"}, 400

        response = await service.execute_transition(
            entity_id=entity_id,
            transition=transition_name,
            entity_class=ModelVersion.ENTITY_NAME,
            entity_version=str(ModelVersion.ENTITY_VERSION),
        )

        return _to_entity_dict(response.data), 200
    except Exception as e:
        logger.exception("Error triggering transition: %s", str(e))
        return {"error": str(e)}, 500
