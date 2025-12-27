import logging
from typing import Any, Dict

from quart import Blueprint, jsonify, request
from quart.typing import ResponseReturnValue
from quart_schema import operation_id, tag, validate

from application.entity.market_data import MarketData
from application.models import ErrorResponse, MarketDataRequest, MarketDataResponse
from services.services import get_entity_service

logger = logging.getLogger(__name__)


class _ServiceProxy:
    def __getattr__(self, name: str) -> Any:
        return getattr(get_entity_service(), name)


service = _ServiceProxy()

market_data_bp = Blueprint("market_data", __name__, url_prefix="/api/market-data")


@market_data_bp.route("", methods=["POST"])
@tag(["market-data"])
@operation_id("create_market_data")
@validate(
    request=MarketDataRequest,
    responses={201: (MarketDataResponse, None), 400: (ErrorResponse, None)},
)
async def create_market_data(data: MarketDataRequest) -> ResponseReturnValue:
    """Create new market data entry."""
    try:
        entity_data = data.model_dump(by_alias=True)
        response = await service.save(
            entity=entity_data,
            entity_class=MarketData.ENTITY_NAME,
            entity_version=str(MarketData.ENTITY_VERSION),
        )
        logger.info(f"Created market data for {data.symbol}")
        return _to_dict(response.data), 201
    except Exception as e:
        logger.error(f"Error creating market data: {str(e)}")
        return {"error": str(e), "code": "INTERNAL_ERROR"}, 500


@market_data_bp.route("/<entity_id>", methods=["GET"])
@tag(["market-data"])
@operation_id("get_market_data")
@validate(responses={200: (MarketDataResponse, None), 404: (ErrorResponse, None)})
async def get_market_data(entity_id: str) -> ResponseReturnValue:
    """Get market data by ID."""
    try:
        response = await service.get_by_id(
            entity_id=entity_id,
            entity_class=MarketData.ENTITY_NAME,
            entity_version=str(MarketData.ENTITY_VERSION),
        )
        if not response:
            return {"error": "Not found"}, 404
        return _to_dict(response.data), 200
    except Exception as e:
        logger.error(f"Error getting market data: {str(e)}")
        return {"error": str(e)}, 500


@market_data_bp.route("", methods=["GET"])
@tag(["market-data"])
@operation_id("list_market_data")
@validate(responses={200: (Dict[str, Any], None)})
async def list_market_data() -> ResponseReturnValue:
    """List all market data."""
    try:
        results = await service.find_all(
            entity_class=MarketData.ENTITY_NAME,
            entity_version=str(MarketData.ENTITY_VERSION),
        )
        entities = [_to_dict(r.data) for r in results]
        return {"entities": entities, "total": len(entities)}, 200
    except Exception as e:
        logger.error(f"Error listing market data: {str(e)}")
        return {"error": str(e)}, 500


@market_data_bp.route("/<entity_id>", methods=["DELETE"])
@tag(["market-data"])
@operation_id("delete_market_data")
@validate(responses={200: (Dict[str, Any], None)})
async def delete_market_data(entity_id: str) -> ResponseReturnValue:
    """Delete market data by ID."""
    try:
        await service.delete_by_id(
            entity_id=entity_id,
            entity_class=MarketData.ENTITY_NAME,
            entity_version=str(MarketData.ENTITY_VERSION),
        )
        logger.info(f"Deleted market data {entity_id}")
        return {"success": True, "message": "Deleted"}, 200
    except Exception as e:
        logger.error(f"Error deleting market data: {str(e)}")
        return {"error": str(e)}, 500


def _to_dict(data: Any) -> Dict[str, Any]:
    """Convert entity to dict."""
    return data.model_dump(by_alias=True) if hasattr(data, "model_dump") else data
