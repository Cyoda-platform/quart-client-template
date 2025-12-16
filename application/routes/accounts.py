"""
Account management API routes for the trading platform.

Provides REST endpoints for Account CRUD operations.
"""

import logging
from typing import Any, Dict

from quart import Blueprint
from quart_schema import validate_request, validate_response

from application.entity.account.version_1.account import Account
from services.services import get_entity_service

logger = logging.getLogger(__name__)

accounts_bp = Blueprint("accounts", __name__, url_prefix="/api/accounts")


@accounts_bp.route("", methods=["POST"])
@validate_request(Account)
@validate_response(Account, status_code=201)
async def create_account(data: Account) -> tuple[Dict[str, Any], int]:
    """Create a new Account."""
    try:
        entity_service = get_entity_service()
        account_data = data.model_dump(by_alias=True)
        response = await entity_service.save(
            entity=account_data,
            entity_class=Account.ENTITY_NAME,
            entity_version=str(Account.ENTITY_VERSION),
        )
        account_data["id"] = response.metadata.id
        account_data["state"] = response.metadata.state
        logger.info(f"Account created: {response.metadata.id}")
        return account_data, 201
    except Exception as e:
        logger.error(f"Failed to create Account: {str(e)}")
        return {"error": str(e)}, 400


@accounts_bp.route("/<account_id>", methods=["GET"])
async def get_account(account_id: str) -> tuple[Dict[str, Any], int]:
    """Get Account by technical ID."""
    try:
        entity_service = get_entity_service()
        response = await entity_service.get_by_id(
            entity_id=account_id,
            entity_class=Account.ENTITY_NAME,
            entity_version=str(Account.ENTITY_VERSION),
        )
        if response is None:
            return {"error": "Account not found"}, 404
        account_data = response.data.model_dump(by_alias=True)
        account_data["id"] = response.metadata.id
        account_data["state"] = response.metadata.state
        return account_data, 200
    except Exception as e:
        logger.error(f"Failed to get Account: {str(e)}")
        return {"error": str(e)}, 404


@accounts_bp.route("/<account_id>", methods=["PUT"])
@validate_request(Account)
async def update_account(account_id: str, data: Account) -> tuple[Dict[str, Any], int]:
    """Update a Account."""
    try:
        entity_service = get_entity_service()
        account_data = data.model_dump(by_alias=True)
        response = await entity_service.update(
            entity_id=account_id,
            entity=account_data,
            entity_class=Account.ENTITY_NAME,
            entity_version=str(Account.ENTITY_VERSION),
        )
        account_data["id"] = response.metadata.id
        account_data["state"] = response.metadata.state
        logger.info(f"Account updated: {account_id}")
        return account_data, 200
    except Exception as e:
        logger.error(f"Failed to update Account: {str(e)}")
        return {"error": str(e)}, 400


@accounts_bp.route("/<account_id>", methods=["DELETE"])
async def delete_account(account_id: str) -> tuple[Dict[str, str], int]:
    """Delete a Account."""
    try:
        entity_service = get_entity_service()
        await entity_service.delete_by_id(
            entity_id=account_id,
            entity_class=Account.ENTITY_NAME,
            entity_version=str(Account.ENTITY_VERSION),
        )
        logger.info(f"Account deleted: {account_id}")
        return {"message": "Account deleted successfully"}, 200
    except Exception as e:
        logger.error(f"Failed to delete Account: {str(e)}")
        return {"error": str(e)}, 400
