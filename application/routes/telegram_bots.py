"""
TelegramBot Routes for Telegram bot application.

Manages all TelegramBot-related API endpoints.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from quart import Blueprint, jsonify, request
from quart.typing import ResponseReturnValue
from quart_schema import operation_id, tag, validate

from services.services import get_entity_service
from application.entity.telegram_bot import TelegramBot

logger = logging.getLogger(__name__)


class _ServiceProxy:
    def __getattr__(self, name: str) -> Any:
        return getattr(get_entity_service(), name)


service = _ServiceProxy()


def _to_entity_dict(data: Any) -> Dict[str, Any]:
    return data.model_dump(by_alias=True) if hasattr(data, "model_dump") else data


telegram_bots_bp = Blueprint("telegram_bots", __name__, url_prefix="/api/telegram-bots")


@telegram_bots_bp.route("", methods=["POST"])
@tag(["telegram-bots"])
@operation_id("create_telegram_bot")
@validate(responses={201: (Dict[str, Any], None), 400: (Dict[str, str], None)})
async def create_telegram_bot(data: TelegramBot) -> ResponseReturnValue:
    """Create a new TelegramBot"""
    try:
        entity_data = data.model_dump(by_alias=True)
        response = await service.save(
            entity=entity_data,
            entity_class=TelegramBot.ENTITY_NAME,
            entity_version=str(TelegramBot.ENTITY_VERSION),
        )
        logger.info("Created TelegramBot with ID: %s", response.metadata.id)
        return _to_entity_dict(response.data), 201
    except ValueError as e:
        logger.warning("Validation error: %s", str(e))
        return {"error": str(e)}, 400
    except Exception as e:
        logger.exception("Error creating TelegramBot: %s", str(e))
        return {"error": str(e)}, 500


@telegram_bots_bp.route("/<entity_id>", methods=["GET"])
@tag(["telegram-bots"])
@operation_id("get_telegram_bot")
@validate(responses={200: (Dict[str, Any], None), 404: (Dict[str, str], None)})
async def get_telegram_bot(entity_id: str) -> ResponseReturnValue:
    """Get TelegramBot by ID"""
    try:
        if not entity_id or len(entity_id.strip()) == 0:
            return {"error": "Entity ID is required"}, 400

        response = await service.get_by_id(
            entity_id=entity_id,
            entity_class=TelegramBot.ENTITY_NAME,
            entity_version=str(TelegramBot.ENTITY_VERSION),
        )

        if not response:
            return {"error": "TelegramBot not found"}, 404

        return _to_entity_dict(response.data), 200
    except Exception as e:
        logger.exception("Error getting TelegramBot: %s", str(e))
        return {"error": str(e)}, 500


@telegram_bots_bp.route("", methods=["GET"])
@tag(["telegram-bots"])
@operation_id("list_telegram_bots")
@validate(responses={200: (Dict[str, Any], None)})
async def list_telegram_bots() -> ResponseReturnValue:
    """List all TelegramBots"""
    try:
        entities = await service.find_all(
            entity_class=TelegramBot.ENTITY_NAME,
            entity_version=str(TelegramBot.ENTITY_VERSION),
        )
        entity_list = [_to_entity_dict(r.data) for r in entities]
        return {"entities": entity_list, "total": len(entity_list)}, 200
    except Exception as e:
        logger.exception("Error listing TelegramBots: %s", str(e))
        return {"error": str(e)}, 500


@telegram_bots_bp.route("/<entity_id>", methods=["PUT"])
@tag(["telegram-bots"])
@operation_id("update_telegram_bot")
@validate(responses={200: (Dict[str, Any], None), 404: (Dict[str, str], None)})
async def update_telegram_bot(entity_id: str, data: TelegramBot) -> ResponseReturnValue:
    """Update TelegramBot"""
    try:
        if not entity_id or len(entity_id.strip()) == 0:
            return {"error": "Entity ID is required"}, 400

        entity_data: Dict[str, Any] = data.model_dump(by_alias=True)
        transition: Optional[str] = request.args.get("transition")

        response = await service.update(
            entity_id=entity_id,
            entity=entity_data,
            entity_class=TelegramBot.ENTITY_NAME,
            transition=transition,
            entity_version=str(TelegramBot.ENTITY_VERSION),
        )

        logger.info("Updated TelegramBot %s", entity_id)
        return jsonify(_to_entity_dict(response.data)), 200
    except Exception as e:
        logger.exception("Error updating TelegramBot: %s", str(e))
        return {"error": str(e)}, 500


@telegram_bots_bp.route("/<entity_id>", methods=["DELETE"])
@tag(["telegram-bots"])
@operation_id("delete_telegram_bot")
@validate(responses={200: (Dict[str, Any], None), 404: (Dict[str, str], None)})
async def delete_telegram_bot(entity_id: str) -> ResponseReturnValue:
    """Delete TelegramBot"""
    try:
        if not entity_id or len(entity_id.strip()) == 0:
            return {"error": "Entity ID is required"}, 400

        await service.delete_by_id(
            entity_id=entity_id,
            entity_class=TelegramBot.ENTITY_NAME,
            entity_version=str(TelegramBot.ENTITY_VERSION),
        )

        logger.info("Deleted TelegramBot %s", entity_id)
        return {"success": True, "message": "TelegramBot deleted"}, 200
    except Exception as e:
        logger.exception("Error deleting TelegramBot: %s", str(e))
        return {"error": str(e)}, 500
