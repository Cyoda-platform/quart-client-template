import logging
from typing import Any, Dict

from quart import Blueprint
from quart.typing import ResponseReturnValue
from quart_schema import operation_id, tag, validate

from application.entity.account.version_1.account import Account
from services.services import get_entity_service

logger = logging.getLogger(__name__)

accounts_bp = Blueprint("accounts", __name__, url_prefix="/api/accounts")


def _to_entity_dict(data: Any) -> Dict[str, Any]:
    return data.model_dump(by_alias=True) if hasattr(data, "model_dump") else data


@accounts_bp.route("", methods=["POST"])
@tag(["accounts"])
@operation_id("create_account")
@validate(request=Account, responses={201: (Dict[str, Any], None)})
async def create_account(data: Account) -> ResponseReturnValue:
    """Create a new trading account"""
    try:
        entity_data = data.model_dump(by_alias=True)
        response = await get_entity_service().save(
            entity=entity_data,
            entity_class=Account.ENTITY_NAME,
            entity_version=str(Account.ENTITY_VERSION),
        )
        logger.info(f"Created account {response.metadata.id}")
        return _to_entity_dict(response.data), 201
    except Exception as e:
        logger.exception(f"Error creating account: {str(e)}")
        return {"error": str(e)}, 400


@accounts_bp.route("/<account_id>", methods=["GET"])
@tag(["accounts"])
@operation_id("get_account")
@validate(responses={200: (Dict[str, Any], None)})
async def get_account(account_id: str) -> ResponseReturnValue:
    """Get account by ID"""
    try:
        response = await get_entity_service().get_by_id(
            entity_id=account_id,
            entity_class=Account.ENTITY_NAME,
            entity_version=str(Account.ENTITY_VERSION),
        )
        if not response:
            return {"error": "Account not found"}, 404
        return _to_entity_dict(response.data), 200
    except Exception as e:
        logger.exception(f"Error getting account: {str(e)}")
        return {"error": str(e)}, 400


@accounts_bp.route("", methods=["GET"])
@tag(["accounts"])
@operation_id("list_accounts")
@validate(responses={200: (Dict[str, Any], None)})
async def list_accounts() -> ResponseReturnValue:
    """List all accounts"""
    try:
        entities = await get_entity_service().find_all(
            entity_class=Account.ENTITY_NAME,
            entity_version=str(Account.ENTITY_VERSION),
        )
        entity_list = [_to_entity_dict(r.data) for r in entities]
        return {"accounts": entity_list, "total": len(entity_list)}, 200
    except Exception as e:
        logger.exception(f"Error listing accounts: {str(e)}")
        return {"error": str(e)}, 400
