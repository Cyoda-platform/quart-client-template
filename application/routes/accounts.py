"""
Account Routes for Institutional Trading Platform

Manages all Account-related API endpoints.
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from quart import Blueprint
from quart.typing import ResponseReturnValue
from quart_schema import operation_id, tag, validate

from common.exception import is_not_found
from services.services import get_entity_service

from application.entity.account.version_1.account import Account


class _ServiceProxy:
    def __getattr__(self, name: str) -> Any:
        return getattr(get_entity_service(), name)


service = _ServiceProxy()
logger = logging.getLogger(__name__)


def _to_entity_dict(data: Any) -> Dict[str, Any]:
    return data.model_dump(by_alias=True) if hasattr(data, "model_dump") else data


accounts_bp = Blueprint("accounts", __name__, url_prefix="/api/accounts")


@accounts_bp.route("", methods=["POST"])
@tag(["accounts"])
@operation_id("create_account")
@validate(request=Account, responses={201: (dict, None), 400: (dict, None), 500: (dict, None)})
async def create_account(data: Account) -> ResponseReturnValue:
    """Create a new account"""
    try:
        entity_data = data.model_dump(by_alias=True)
        response = await service.save(
            entity=entity_data,
            entity_class=Account.ENTITY_NAME,
            entity_version=str(Account.ENTITY_VERSION),
        )
        return _to_entity_dict(response.data), 201
    except Exception as e:
        logger.error(f"Error creating account: {str(e)}")
        return {"error": str(e)}, 500


@accounts_bp.route("/<entity_id>", methods=["GET"])
@tag(["accounts"])
@operation_id("get_account")
@validate(responses={200: (dict, None), 404: (dict, None), 500: (dict, None)})
async def get_account(entity_id: str) -> ResponseReturnValue:
    """Get an account by ID"""
    try:
        response = await service.get(
            entity_id=entity_id,
            entity_class=Account.ENTITY_NAME,
            entity_version=str(Account.ENTITY_VERSION),
        )
        if is_not_found(response):
            return {"error": "Account not found"}, 404
        return _to_entity_dict(response.data), 200
    except Exception as e:
        logger.error(f"Error getting account: {str(e)}")
        return {"error": str(e)}, 500


@accounts_bp.route("", methods=["GET"])
@tag(["accounts"])
@operation_id("list_accounts")
@validate(responses={200: (dict, None), 500: (dict, None)})
async def list_accounts() -> ResponseReturnValue:
    """List all accounts"""
    try:
        response = await service.list(
            entity_class=Account.ENTITY_NAME,
            entity_version=str(Account.ENTITY_VERSION),
            limit=100,
            offset=0,
        )
        return {"accounts": [_to_entity_dict(item) for item in response.data]}, 200
    except Exception as e:
        logger.error(f"Error listing accounts: {str(e)}")
        return {"error": str(e)}, 500


@accounts_bp.route("/<entity_id>/transition", methods=["POST"])
@tag(["accounts"])
@operation_id("transition_account")
@validate(request=dict, responses={200: (dict, None), 400: (dict, None), 500: (dict, None)})
async def transition_account(entity_id: str, data: dict) -> ResponseReturnValue:
    """Trigger a workflow transition on an account"""
    try:
        transition_name = data.get("transitionName")
        if not transition_name:
            return {"error": "transitionName is required"}, 400

        response = await service.transition(
            entity_id=entity_id,
            entity_class=Account.ENTITY_NAME,
            entity_version=str(Account.ENTITY_VERSION),
            transition_name=transition_name,
        )
        return _to_entity_dict(response.data), 200
    except Exception as e:
        logger.error(f"Error transitioning account: {str(e)}")
        return {"error": str(e)}, 500

