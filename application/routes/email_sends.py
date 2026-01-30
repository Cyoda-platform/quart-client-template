"""
EmailSend Routes for Weekly Cat Fact Subscription Application

Manages all EmailSend-related API endpoints including CRUD operations
and send job management.
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from quart import Blueprint, jsonify, request
from quart.typing import ResponseReturnValue
from quart_schema import operation_id, tag, validate

from services.services import get_entity_service
from application.entity.email_send.version_1.email_send import EmailSend


class _ServiceProxy:
    def __getattr__(self, name: str) -> Any:
        return getattr(get_entity_service(), name)


service = _ServiceProxy()
logger = logging.getLogger(__name__)


def _to_entity_dict(data: Any) -> Dict[str, Any]:
    return data.model_dump(by_alias=True) if hasattr(data, "model_dump") else data


email_sends_bp = Blueprint("email_sends", __name__, url_prefix="/api/email-sends")


@email_sends_bp.route("", methods=["POST"])
@tag(["email-sends"])
@operation_id("create_email_send")
@validate(
    request=EmailSend,
    responses={
        201: (dict, None),
        400: (dict, None),
        500: (dict, None),
    },
)
async def create_email_send(data: EmailSend) -> ResponseReturnValue:
    """Create a new EmailSend job"""
    try:
        entity_data = data.model_dump(by_alias=True)
        response = await service.save(
            entity=entity_data,
            entity_class=EmailSend.ENTITY_NAME,
            entity_version=str(EmailSend.ENTITY_VERSION),
        )
        logger.info("Created EmailSend with ID: %s", response.metadata.id)
        return _to_entity_dict(response.data), 201
    except ValueError as e:
        logger.warning("Validation error: %s", str(e))
        return {"error": str(e), "code": "VALIDATION_ERROR"}, 400
    except Exception as e:
        logger.exception("Error creating EmailSend: %s", str(e))
        return {"error": str(e), "code": "INTERNAL_ERROR"}, 500


@email_sends_bp.route("/<entity_id>", methods=["GET"])
@tag(["email-sends"])
@operation_id("get_email_send")
@validate(
    responses={
        200: (dict, None),
        404: (dict, None),
        500: (dict, None),
    }
)
async def get_email_send(entity_id: str) -> ResponseReturnValue:
    """Get EmailSend by ID"""
    try:
        if not entity_id or len(entity_id.strip()) == 0:
            return {"error": "Entity ID is required", "code": "INVALID_ID"}, 400

        response = await service.get_by_id(
            entity_id=entity_id,
            entity_class=EmailSend.ENTITY_NAME,
            entity_version=str(EmailSend.ENTITY_VERSION),
        )

        if not response:
            return {"error": "EmailSend not found", "code": "NOT_FOUND"}, 404

        return _to_entity_dict(response.data), 200
    except Exception as e:
        logger.exception("Error getting EmailSend: %s", str(e))
        return {"error": str(e), "code": "INTERNAL_ERROR"}, 500


@email_sends_bp.route("/<entity_id>", methods=["DELETE"])
@tag(["email-sends"])
@operation_id("delete_email_send")
@validate(
    responses={
        200: (dict, None),
        404: (dict, None),
        500: (dict, None),
    }
)
async def delete_email_send(entity_id: str) -> ResponseReturnValue:
    """Delete EmailSend by ID"""
    try:
        if not entity_id or len(entity_id.strip()) == 0:
            return {"error": "Entity ID is required", "code": "INVALID_ID"}, 400

        await service.delete(
            entity_id=entity_id,
            entity_class=EmailSend.ENTITY_NAME,
            entity_version=str(EmailSend.ENTITY_VERSION),
        )

        return {"message": "EmailSend deleted successfully"}, 200
    except Exception as e:
        logger.exception("Error deleting EmailSend: %s", str(e))
        return {"error": str(e), "code": "INTERNAL_ERROR"}, 500

