import logging
from typing import Any, Dict

from quart import Blueprint
from quart.typing import ResponseReturnValue
from quart_schema import operation_id, tag, validate

from application.entity.market_data.version_1.market_data import MarketData
from services.services import get_entity_service

logger = logging.getLogger(__name__)

market_data_bp = Blueprint("market_data", __name__, url_prefix="/api/market-data")


def _to_entity_dict(data: Any) -> Dict[str, Any]:
    return data.model_dump(by_alias=True) if hasattr(data, "model_dump") else data


@market_data_bp.route("", methods=["POST"])
@tag(["market-data"])
@operation_id("create_market_data")
@validate(request=MarketData, responses={201: (Dict[str, Any], None)})
async def create_market_data(data: MarketData) -> ResponseReturnValue:
    """Create market data entry"""
    try:
        entity_data = data.model_dump(by_alias=True)
        response = await get_entity_service().save(
            entity=entity_data,
            entity_class=MarketData.ENTITY_NAME,
            entity_version=str(MarketData.ENTITY_VERSION),
        )
        logger.info(f"Created market data {response.metadata.id}")
        return _to_entity_dict(response.data), 201
    except Exception as e:
        logger.exception(f"Error creating market data: {str(e)}")
        return {"error": str(e)}, 400


@market_data_bp.route("/<data_id>", methods=["GET"])
@tag(["market-data"])
@operation_id("get_market_data")
@validate(responses={200: (Dict[str, Any], None)})
async def get_market_data(data_id: str) -> ResponseReturnValue:
    """Get market data by ID"""
    try:
        response = await get_entity_service().get_by_id(
            entity_id=data_id,
            entity_class=MarketData.ENTITY_NAME,
            entity_version=str(MarketData.ENTITY_VERSION),
        )
        if not response:
            return {"error": "Market data not found"}, 404
        return _to_entity_dict(response.data), 200
    except Exception as e:
        logger.exception(f"Error getting market data: {str(e)}")
        return {"error": str(e)}, 400


@market_data_bp.route("", methods=["GET"])
@tag(["market-data"])
@operation_id("list_market_data")
@validate(responses={200: (Dict[str, Any], None)})
async def list_market_data() -> ResponseReturnValue:
    """List all market data"""
    try:
        entities = await get_entity_service().find_all(
            entity_class=MarketData.ENTITY_NAME,
            entity_version=str(MarketData.ENTITY_VERSION),
        )
        entity_list = [_to_entity_dict(r.data) for r in entities]
        return {"market_data": entity_list, "total": len(entity_list)}, 200
    except Exception as e:
        logger.exception(f"Error listing market data: {str(e)}")
        return {"error": str(e)}, 400
