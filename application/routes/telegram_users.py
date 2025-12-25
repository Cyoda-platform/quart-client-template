"""
TelegramUser Routes for Telegram bot application.

Manages all TelegramUser-related API endpoints.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from quart import Blueprint, jsonify, request
from quart.typing import ResponseReturnValue
from quart_schema import operation_id, tag, validate

from services.services import get_entity_service
from application.entity.telegram_user import TelegramUser

logger = logging.getLogger(__name__)


class _ServiceProxy:
    def __getattr__(self, name: str) -> Any:
        return getattr(get_entity_service(), name)


service = _ServiceProxy()


def _to_entity_dict(data: Any) -> Dict[str, Any]:
    return data.model_dump(by_alias=True) if hasattr(data, "model_dump") else data


telegram_users_bp = Blueprint(
    "telegram_users", __name__, url_prefix="/api/telegram-users"
)


@telegram_users_bp.route("", methods=["POST"])
@tag(["telegram-users"])
@operation_id("create_telegram_user")
@validate(responses={201: (Dict[str, Any], None), 400: (Dict[str, str], None)})
async def create_telegram_user(data: TelegramUser) -> ResponseReturnValue:
    """Create a new TelegramUser"""
    try:
        entity_data = data.model_dump(by_alias=True)
        response = await service.save(
            entity=entity_data,
            entity_class=TelegramUser.ENTITY_NAME,
            entity_version=str(TelegramUser.ENTITY_VERSION),
        )
        logger.info("Created TelegramUser with ID: %s", response.metadata.id)
        return _to_entity_dict(response.data), 201
    except ValueError as e:
        logger.warning("Validation error: %s", str(e))
        return {"error": str(e)}, 400
    except Exception as e:
        logger.exception("Error creating TelegramUser: %s", str(e))
        return {"error": str(e)}, 500


@telegram_users_bp.route("/<entity_id>", methods=["GET"])
@tag(["telegram-users"])
@operation_id("get_telegram_user")
@validate(responses={200: (Dict[str, Any], None), 404: (Dict[str, str], None)})
async def get_telegram_user(entity_id: str) -> ResponseReturnValue:
    """Get TelegramUser by ID"""
    try:
        if not entity_id or len(entity_id.strip()) == 0:
            return {"error": "Entity ID is required"}, 400

        response = await service.get_by_id(
            entity_id=entity_id,
            entity_class=TelegramUser.ENTITY_NAME,
            entity_version=str(TelegramUser.ENTITY_VERSION),
        )

        if not response:
            return {"error": "TelegramUser not found"}, 404

        return _to_entity_dict(response.data), 200
    except Exception as e:
        logger.exception("Error getting TelegramUser: %s", str(e))
        return {"error": str(e)}, 500


@telegram_users_bp.route("", methods=["GET"])
@tag(["telegram-users"])
@operation_id("list_telegram_users")
@validate(responses={200: (Dict[str, Any], None)})
async def list_telegram_users() -> ResponseReturnValue:
    """List all TelegramUsers"""
    try:
        entities = await service.find_all(
            entity_class=TelegramUser.ENTITY_NAME,
            entity_version=str(TelegramUser.ENTITY_VERSION),
        )
        entity_list = [_to_entity_dict(r.data) for r in entities]
        return {"entities": entity_list, "total": len(entity_list)}, 200
    except Exception as e:
        logger.exception("Error listing TelegramUsers: %s", str(e))
        return {"error": str(e)}, 500


@telegram_users_bp.route("/<entity_id>", methods=["PUT"])
@tag(["telegram-users"])
@operation_id("update_telegram_user")
@validate(responses={200: (Dict[str, Any], None), 404: (Dict[str, str], None)})
async def update_telegram_user(
    entity_id: str, data: TelegramUser
) -> ResponseReturnValue:
    """Update TelegramUser"""
    try:
        if not entity_id or len(entity_id.strip()) == 0:
            return {"error": "Entity ID is required"}, 400

        entity_data: Dict[str, Any] = data.model_dump(by_alias=True)
        transition: Optional[str] = request.args.get("transition")

        response = await service.update(
            entity_id=entity_id,
            entity=entity_data,
            entity_class=TelegramUser.ENTITY_NAME,
            transition=transition,
            entity_version=str(TelegramUser.ENTITY_VERSION),
        )

        logger.info("Updated TelegramUser %s", entity_id)
        return jsonify(_to_entity_dict(response.data)), 200
    except Exception as e:
        logger.exception("Error updating TelegramUser: %s", str(e))
        return {"error": str(e)}, 500


@telegram_users_bp.route("/<entity_id>", methods=["DELETE"])
@tag(["telegram-users"])
@operation_id("delete_telegram_user")
@validate(responses={200: (Dict[str, Any], None), 404: (Dict[str, str], None)})
async def delete_telegram_user(entity_id: str) -> ResponseReturnValue:
    """Delete TelegramUser"""
    try:
        if not entity_id or len(entity_id.strip()) == 0:
            return {"error": "Entity ID is required"}, 400

        await service.delete_by_id(
            entity_id=entity_id,
            entity_class=TelegramUser.ENTITY_NAME,
            entity_version=str(TelegramUser.ENTITY_VERSION),
        )

        logger.info("Deleted TelegramUser %s", entity_id)
        return {"success": True, "message": "TelegramUser deleted"}, 200
    except Exception as e:
        logger.exception("Error deleting TelegramUser: %s", str(e))
        return {"error": str(e)}, 500
