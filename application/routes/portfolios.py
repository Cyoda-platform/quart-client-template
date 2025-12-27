import logging
from typing import Any, Dict

from quart import Blueprint, jsonify, request
from quart.typing import ResponseReturnValue
from quart_schema import operation_id, tag, validate

from application.entity.portfolio import Portfolio
from application.models import PortfolioRequest, PortfolioResponse, ErrorResponse
from services.services import get_entity_service

logger = logging.getLogger(__name__)


class _ServiceProxy:
    def __getattr__(self, name: str) -> Any:
        return getattr(get_entity_service(), name)


service = _ServiceProxy()

portfolios_bp = Blueprint("portfolios", __name__, url_prefix="/api/portfolios")


@portfolios_bp.route("", methods=["POST"])
@tag(["portfolios"])
@operation_id("create_portfolio")
@validate(
    request=PortfolioRequest,
    responses={201: (PortfolioResponse, None), 400: (ErrorResponse, None)},
)
async def create_portfolio(data: PortfolioRequest) -> ResponseReturnValue:
    """Create new portfolio."""
    try:
        entity_data = data.model_dump(by_alias=True)
        response = await service.save(
            entity=entity_data,
            entity_class=Portfolio.ENTITY_NAME,
            entity_version=str(Portfolio.ENTITY_VERSION),
        )
        logger.info(f"Created portfolio {data.account_id}")
        return _to_dict(response.data), 201
    except Exception as e:
        logger.error(f"Error creating portfolio: {str(e)}")
        return {"error": str(e), "code": "INTERNAL_ERROR"}, 500


@portfolios_bp.route("/<entity_id>", methods=["GET"])
@tag(["portfolios"])
@operation_id("get_portfolio")
@validate(responses={200: (PortfolioResponse, None), 404: (ErrorResponse, None)})
async def get_portfolio(entity_id: str) -> ResponseReturnValue:
    """Get portfolio by ID."""
    try:
        response = await service.get_by_id(
            entity_id=entity_id,
            entity_class=Portfolio.ENTITY_NAME,
            entity_version=str(Portfolio.ENTITY_VERSION),
        )
        if not response:
            return {"error": "Not found"}, 404
        return _to_dict(response.data), 200
    except Exception as e:
        logger.error(f"Error getting portfolio: {str(e)}")
        return {"error": str(e)}, 500


@portfolios_bp.route("", methods=["GET"])
@tag(["portfolios"])
@operation_id("list_portfolios")
@validate(responses={200: (Dict[str, Any], None)})
async def list_portfolios() -> ResponseReturnValue:
    """List all portfolios."""
    try:
        results = await service.find_all(
            entity_class=Portfolio.ENTITY_NAME,
            entity_version=str(Portfolio.ENTITY_VERSION),
        )
        entities = [_to_dict(r.data) for r in results]
        return {"entities": entities, "total": len(entities)}, 200
    except Exception as e:
        logger.error(f"Error listing portfolios: {str(e)}")
        return {"error": str(e)}, 500


@portfolios_bp.route("/<entity_id>", methods=["PUT"])
@tag(["portfolios"])
@operation_id("update_portfolio")
@validate(
    request=PortfolioRequest,
    responses={200: (PortfolioResponse, None), 404: (ErrorResponse, None)},
)
async def update_portfolio(entity_id: str, data: PortfolioRequest) -> ResponseReturnValue:
    """Update portfolio."""
    try:
        entity_data = data.model_dump(by_alias=True)
        response = await service.update(
            entity_id=entity_id,
            entity=entity_data,
            entity_class=Portfolio.ENTITY_NAME,
            entity_version=str(Portfolio.ENTITY_VERSION),
        )
        logger.info(f"Updated portfolio {entity_id}")
        return _to_dict(response.data), 200
    except Exception as e:
        logger.error(f"Error updating portfolio: {str(e)}")
        return {"error": str(e)}, 500


@portfolios_bp.route("/<entity_id>", methods=["DELETE"])
@tag(["portfolios"])
@operation_id("delete_portfolio")
@validate(responses={200: (Dict[str, Any], None)})
async def delete_portfolio(entity_id: str) -> ResponseReturnValue:
    """Delete portfolio by ID."""
    try:
        await service.delete_by_id(
            entity_id=entity_id,
            entity_class=Portfolio.ENTITY_NAME,
            entity_version=str(Portfolio.ENTITY_VERSION),
        )
        logger.info(f"Deleted portfolio {entity_id}")
        return {"success": True, "message": "Deleted"}, 200
    except Exception as e:
        logger.error(f"Error deleting portfolio: {str(e)}")
        return {"error": str(e)}, 500


def _to_dict(data: Any) -> Dict[str, Any]:
    """Convert entity to dict."""
    return data.model_dump(by_alias=True) if hasattr(data, "model_dump") else data

