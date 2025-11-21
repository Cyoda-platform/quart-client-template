"""
Attachment Routes for Project Management Application

Manages all Attachment-related API endpoints including CRUD operations
and file management functionality.
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from quart import Blueprint, request
from quart.typing import ResponseReturnValue

from services.services import get_entity_service
from application.entity.attachment.version_1.attachment import Attachment

class _ServiceProxy:
    def __getattr__(self, name: str) -> Any:
        return getattr(get_entity_service(), name)

service = _ServiceProxy()
logger = logging.getLogger(__name__)

def _to_entity_dict(data: Any) -> Dict[str, Any]:
    return data.model_dump(by_alias=True) if hasattr(data, "model_dump") else data

attachments_bp = Blueprint("attachments", __name__, url_prefix="/api/attachments")

@attachments_bp.route("", methods=["POST"])
async def create_attachment() -> ResponseReturnValue:
    """Create a new Attachment"""
    try:
        data = await request.get_json()
        if not data:
            return {"error": "Request body is required", "code": "INVALID_REQUEST"}, 400

        attachment = Attachment(**data)
        entity_data = attachment.model_dump(by_alias=True)

        response = await service.save(
            entity=entity_data,
            entity_class=Attachment.ENTITY_NAME,
            entity_version=str(Attachment.ENTITY_VERSION),
        )

        logger.info("Created Attachment with ID: %s", response.metadata.id)
        return _to_entity_dict(response.data), 201

    except ValueError as e:
        logger.warning("Validation error creating Attachment: %s", str(e))
        return {"error": str(e), "code": "VALIDATION_ERROR"}, 400
    except Exception as e:
        logger.exception("Error creating Attachment: %s", str(e))
        return {"error": str(e), "code": "INTERNAL_ERROR"}, 500

@attachments_bp.route("/<entity_id>", methods=["GET"])
async def get_attachment(entity_id: str) -> ResponseReturnValue:
    """Get Attachment by ID"""
    try:
        if not entity_id or len(entity_id.strip()) == 0:
            return {"error": "Entity ID is required", "code": "INVALID_ID"}, 400

        response = await service.get_by_id(
            entity_id=entity_id,
            entity_class=Attachment.ENTITY_NAME,
            entity_version=str(Attachment.ENTITY_VERSION),
        )

        if not response:
            return {"error": "Attachment not found", "code": "NOT_FOUND"}, 404

        return _to_entity_dict(response.data), 200

    except Exception as e:
        logger.exception("Error getting Attachment: %s", str(e))
        return {"error": str(e), "code": "INTERNAL_ERROR"}, 500

@attachments_bp.route("", methods=["GET"])
async def list_attachments() -> ResponseReturnValue:
    """List Attachments with filtering"""
    try:
        task_id = request.args.get("task_id")
        uploaded_by = request.args.get("uploaded_by")
        content_type = request.args.get("content_type")
        limit = int(request.args.get("limit", 50))
        offset = int(request.args.get("offset", 0))

        conditions = []
        if task_id:
            conditions.append({
                "field": "task_id",
                "operator": "EQUALS",
                "value": task_id
            })
        if uploaded_by:
            conditions.append({
                "field": "uploaded_by",
                "operator": "EQUALS",
                "value": uploaded_by
            })
        if content_type:
            conditions.append({
                "field": "content_type",
                "operator": "EQUALS",
                "value": content_type
            })

        response = await service.search(
            entity_class=Attachment.ENTITY_NAME,
            entity_version=str(Attachment.ENTITY_VERSION),
            conditions=conditions,
            limit=limit,
            offset=offset
        )

        attachments = []
        if response and response.entities:
            attachments = [_to_entity_dict(entity) for entity in response.entities]

        return {
            "attachments": attachments,
            "total": len(attachments),
            "limit": limit,
            "offset": offset
        }, 200

    except Exception as e:
        logger.exception("Error listing Attachments: %s", str(e))
        return {"error": str(e), "code": "INTERNAL_ERROR"}, 500

@attachments_bp.route("/<entity_id>", methods=["DELETE"])
async def delete_attachment(entity_id: str) -> ResponseReturnValue:
    """Delete Attachment by ID"""
    try:
        if not entity_id or len(entity_id.strip()) == 0:
            return {"error": "Entity ID is required", "code": "INVALID_ID"}, 400

        existing_response = await service.get_by_id(
            entity_id=entity_id,
            entity_class=Attachment.ENTITY_NAME,
            entity_version=str(Attachment.ENTITY_VERSION),
        )

        if not existing_response:
            return {"error": "Attachment not found", "code": "NOT_FOUND"}, 404

        await service.delete(
            entity_id=entity_id,
            entity_class=Attachment.ENTITY_NAME,
            entity_version=str(Attachment.ENTITY_VERSION),
        )

        logger.info("Deleted Attachment with ID: %s", entity_id)
        return {"message": "Attachment deleted successfully"}, 200

    except Exception as e:
        logger.exception("Error deleting Attachment: %s", str(e))
        return {"error": str(e), "code": "INTERNAL_ERROR"}, 500

@attachments_bp.route("/<entity_id>/transition", methods=["POST"])
async def transition_attachment(entity_id: str) -> ResponseReturnValue:
    """Transition Attachment state"""
    try:
        if not entity_id or len(entity_id.strip()) == 0:
            return {"error": "Entity ID is required", "code": "INVALID_ID"}, 400

        data = await request.get_json()
        if not data or "transition" not in data:
            return {"error": "Transition name is required", "code": "INVALID_REQUEST"}, 400

        transition_name = data["transition"]

        response = await service.transition(
            entity_id=entity_id,
            entity_class=Attachment.ENTITY_NAME,
            entity_version=str(Attachment.ENTITY_VERSION),
            transition_name=transition_name,
        )

        logger.info("Transitioned Attachment %s with transition: %s", entity_id, transition_name)
        return _to_entity_dict(response.data), 200

    except Exception as e:
        logger.exception("Error transitioning Attachment: %s", str(e))
        return {"error": str(e), "code": "INTERNAL_ERROR"}, 500

# Special endpoint for task attachments
@attachments_bp.route("/task/<task_id>", methods=["GET"])
async def get_task_attachments(task_id: str) -> ResponseReturnValue:
    """Get all attachments for a task"""
    try:
        if not task_id or len(task_id.strip()) == 0:
            return {"error": "Task ID is required", "code": "INVALID_ID"}, 400

        response = await service.search(
            entity_class=Attachment.ENTITY_NAME,
            entity_version=str(Attachment.ENTITY_VERSION),
            conditions=[{
                "field": "task_id",
                "operator": "EQUALS",
                "value": task_id
            }]
        )

        attachments = []
        if response and response.entities:
            attachments = [_to_entity_dict(entity) for entity in response.entities]

        return {"attachments": attachments, "total": len(attachments)}, 200

    except Exception as e:
        logger.exception("Error getting task attachments: %s", str(e))
        return {"error": str(e), "code": "INTERNAL_ERROR"}, 500
