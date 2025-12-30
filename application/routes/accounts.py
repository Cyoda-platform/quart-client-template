"""
Account routes for institutional trading platform.
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from quart import Blueprint, jsonify, request
from quart.typing import ResponseReturnValue
from quart_schema import operation_id, tag, validate

from application.entity.account import Account
from common.exception import is_not_found
from services.services import get_entity_service

logger = logging.getLogger(__name__)

accounts_bp = Blueprint("accounts", __name__, url_prefix="/api/accounts")


class _ServiceProxy:
    def __getattr__(self, name: str) -> Any:
        return getattr(get_entity_service(), name)


service = _ServiceProxy()


def _to_entity_dict(data: Dict[str, Any]) -> Dict[str, Any]:
    """Convert entity data to response format."""
    return data if isinstance(data, dict) else data.model_dump(by_alias=True)


@accounts_bp.route("", methods=["POST"])
@tag(["accounts"])
@operation_id("create_account")
@validate(request=Account)
async def create_account(data: Account) -> ResponseReturnValue:
    """Create a new Account"""
    try:
        entity_data = data.model_dump(by_alias=True)
        response = await service.save(
            entity=entity_data,
            entity_class=Account.ENTITY_NAME,
            entity_version=str(Account.ENTITY_VERSION),
        )
        logger.info("Created Account with ID: %s", response.metadata.id)
        return _to_entity_dict(response.data), 201
    except Exception as e:
        logger.error("Error creating account: %s", str(e))
        return {"error": str(e)}, 500


@accounts_bp.route("/<entity_id>", methods=["GET"])
@tag(["accounts"])
@operation_id("get_account")
async def get_account(entity_id: str) -> ResponseReturnValue:
    """Get an Account by ID"""
    try:
        response = await service.get(
            entity_id=entity_id,
            entity_class=Account.ENTITY_NAME,
        )
        if is_not_found(response):
            return {"error": "Not found"}, 404
        return _to_entity_dict(response.data), 200
    except Exception as e:
        logger.error("Error getting account: %s", str(e))
        return {"error": str(e)}, 500


@accounts_bp.route("", methods=["GET"])
@tag(["accounts"])
@operation_id("list_accounts")
async def list_accounts() -> ResponseReturnValue:
    """List all Accounts"""
    try:
        response = await service.list(
            entity_class=Account.ENTITY_NAME,
        )
        return {"data": response.data}, 200
    except Exception as e:
        logger.error("Error listing accounts: %s", str(e))
        return {"error": str(e)}, 500
