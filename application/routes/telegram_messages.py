"""
TelegramMessage Routes for Telegram bot application.

Manages all TelegramMessage-related API endpoints.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from quart import Blueprint, jsonify, request
from quart.typing import ResponseReturnValue
from quart_schema import operation_id, tag, validate

from services.services import get_entity_service
from application.entity.telegram_message import TelegramMessage

logger = logging.getLogger(__name__)


class _ServiceProxy:
    def __getattr__(self, name: str) -> Any:
        return getattr(get_entity_service(), name)


service = _ServiceProxy()


def _to_entity_dict(data: Any) -> Dict[str, Any]:
    return data.model_dump(by_alias=True) if hasattr(data, "model_dump") else data


telegram_messages_bp = Blueprint(
    "telegram_messages", __name__, url_prefix="/api/telegram-messages"
)


@telegram_messages_bp.route("", methods=["POST"])
@tag(["telegram-messages"])
@operation_id("create_telegram_message")
@validate(responses={201: (Dict[str, Any], None), 400: (Dict[str, str], None)})
async def create_telegram_message(data: TelegramMessage) -> ResponseReturnValue:
    """Create a new TelegramMessage"""
    try:
        entity_data = data.model_dump(by_alias=True)
        response = await service.save(
            entity=entity_data,
            entity_class=TelegramMessage.ENTITY_NAME,
            entity_version=str(TelegramMessage.ENTITY_VERSION),
        )
        logger.info("Created TelegramMessage with ID: %s", response.metadata.id)
        return _to_entity_dict(response.data), 201
    except ValueError as e:
        logger.warning("Validation error: %s", str(e))
        return {"error": str(e)}, 400
    except Exception as e:
        logger.exception("Error creating TelegramMessage: %s", str(e))
        return {"error": str(e)}, 500


@telegram_messages_bp.route("/<entity_id>", methods=["GET"])
@tag(["telegram-messages"])
@operation_id("get_telegram_message")
@validate(responses={200: (Dict[str, Any], None), 404: (Dict[str, str], None)})
async def get_telegram_message(entity_id: str) -> ResponseReturnValue:
    """Get TelegramMessage by ID"""
    try:
        if not entity_id or len(entity_id.strip()) == 0:
            return {"error": "Entity ID is required"}, 400

        response = await service.get_by_id(
            entity_id=entity_id,
            entity_class=TelegramMessage.ENTITY_NAME,
            entity_version=str(TelegramMessage.ENTITY_VERSION),
        )

        if not response:
            return {"error": "TelegramMessage not found"}, 404

        return _to_entity_dict(response.data), 200
    except Exception as e:
        logger.exception("Error getting TelegramMessage: %s", str(e))
        return {"error": str(e)}, 500


@telegram_messages_bp.route("", methods=["GET"])
@tag(["telegram-messages"])
@operation_id("list_telegram_messages")
@validate(responses={200: (Dict[str, Any], None)})
async def list_telegram_messages() -> ResponseReturnValue:
    """List all TelegramMessages"""
    try:
        entities = await service.find_all(
            entity_class=TelegramMessage.ENTITY_NAME,
            entity_version=str(TelegramMessage.ENTITY_VERSION),
        )
        entity_list = [_to_entity_dict(r.data) for r in entities]
        return {"entities": entity_list, "total": len(entity_list)}, 200
    except Exception as e:
        logger.exception("Error listing TelegramMessages: %s", str(e))
        return {"error": str(e)}, 500


@telegram_messages_bp.route("/<entity_id>", methods=["PUT"])
@tag(["telegram-messages"])
@operation_id("update_telegram_message")
@validate(responses={200: (Dict[str, Any], None), 404: (Dict[str, str], None)})
async def update_telegram_message(
    entity_id: str, data: TelegramMessage
) -> ResponseReturnValue:
    """Update TelegramMessage"""
    try:
        if not entity_id or len(entity_id.strip()) == 0:
            return {"error": "Entity ID is required"}, 400

        entity_data: Dict[str, Any] = data.model_dump(by_alias=True)
        transition: Optional[str] = request.args.get("transition")

        response = await service.update(
            entity_id=entity_id,
            entity=entity_data,
            entity_class=TelegramMessage.ENTITY_NAME,
            transition=transition,
            entity_version=str(TelegramMessage.ENTITY_VERSION),
        )

        logger.info("Updated TelegramMessage %s", entity_id)
        return jsonify(_to_entity_dict(response.data)), 200
    except Exception as e:
        logger.exception("Error updating TelegramMessage: %s", str(e))
        return {"error": str(e)}, 500


@telegram_messages_bp.route("/<entity_id>", methods=["DELETE"])
@tag(["telegram-messages"])
@operation_id("delete_telegram_message")
@validate(responses={200: (Dict[str, Any], None), 404: (Dict[str, str], None)})
async def delete_telegram_message(entity_id: str) -> ResponseReturnValue:
    """Delete TelegramMessage"""
    try:
        if not entity_id or len(entity_id.strip()) == 0:
            return {"error": "Entity ID is required"}, 400

        await service.delete_by_id(
            entity_id=entity_id,
            entity_class=TelegramMessage.ENTITY_NAME,
            entity_version=str(TelegramMessage.ENTITY_VERSION),
        )

        logger.info("Deleted TelegramMessage %s", entity_id)
        return {"success": True, "message": "TelegramMessage deleted"}, 200
    except Exception as e:
        logger.exception("Error deleting TelegramMessage: %s", str(e))
        return {"error": str(e)}, 500
