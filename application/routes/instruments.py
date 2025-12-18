"""
Instrument Routes for Trading Platform

Manages all Instrument-related API endpoints.
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from quart import Blueprint
from quart.typing import ResponseReturnValue
from quart_schema import operation_id, tag, validate

from common.exception import is_not_found
from services.services import get_entity_service
from application.entity.instrument.version_1.instrument import Instrument

logger = logging.getLogger(__name__)


class _ServiceProxy:
    def __getattr__(self, name: str) -> Any:
        return getattr(get_entity_service(), name)


service = _ServiceProxy()


def _to_entity_dict(data: Any) -> Dict[str, Any]:
    return data.model_dump(by_alias=True) if hasattr(data, "model_dump") else data


instruments_bp = Blueprint("instruments", __name__, url_prefix="/api/instruments")


@instruments_bp.route("", methods=["POST"])
@tag(["instruments"])
@operation_id("create_instrument")
@validate(request=Instrument, responses={201: (dict, None), 400: (dict, None), 500: (dict, None)})
async def create_instrument(data: Instrument) -> ResponseReturnValue:
    """Create a new instrument"""
    try:
        entity_data = data.model_dump(by_alias=True)
        response = await service.save(
            entity=entity_data,
            entity_class=Instrument.ENTITY_NAME,
            entity_version=str(Instrument.ENTITY_VERSION),
        )
        logger.info(f"Created instrument with ID: {response.metadata.id}")
        return _to_entity_dict(response.data), 201
    except Exception as e:
        logger.error(f"Error creating instrument: {str(e)}")
        return {"error": str(e)}, 500


@instruments_bp.route("/<entity_id>", methods=["GET"])
@tag(["instruments"])
@operation_id("get_instrument")
@validate(responses={200: (dict, None), 404: (dict, None), 500: (dict, None)})
async def get_instrument(entity_id: str) -> ResponseReturnValue:
    """Get an instrument by ID"""
    try:
        response = await service.get(
            entity_id=entity_id,
            entity_class=Instrument.ENTITY_NAME,
        )
        if is_not_found(response):
            return {"error": "Instrument not found"}, 404
        return _to_entity_dict(response.data), 200
    except Exception as e:
        logger.error(f"Error getting instrument: {str(e)}")
        return {"error": str(e)}, 500


@instruments_bp.route("", methods=["GET"])
@tag(["instruments"])
@operation_id("list_instruments")
@validate(responses={200: (dict, None), 500: (dict, None)})
async def list_instruments() -> ResponseReturnValue:
    """List all instruments"""
    try:
        response = await service.list(
            entity_class=Instrument.ENTITY_NAME,
            limit=100,
            offset=0,
        )
        instruments = [_to_entity_dict(item) for item in response.data]
        return {"instruments": instruments, "total": len(instruments)}, 200
    except Exception as e:
        logger.error(f"Error listing instruments: {str(e)}")
        return {"error": str(e)}, 500

