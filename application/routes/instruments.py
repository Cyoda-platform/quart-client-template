"""
Instrument routes for institutional trading platform.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from quart import Blueprint, jsonify, request
from quart.typing import ResponseReturnValue
from quart_schema import operation_id, tag, validate, validate_querystring

from common.exception import is_not_found
from services.services import get_entity_service
from application.entity.instrument import Instrument

logger = logging.getLogger(__name__)

instruments_bp = Blueprint("instruments", __name__, url_prefix="/api/instruments")


class _ServiceProxy:
    def __getattr__(self, name: str) -> Any:
        return getattr(get_entity_service(), name)


service = _ServiceProxy()


def _to_entity_dict(data: Dict[str, Any]) -> Dict[str, Any]:
    """Convert entity data to response format."""
    return data if isinstance(data, dict) else data.model_dump(by_alias=True)


@instruments_bp.route("", methods=["POST"])
@tag(["instruments"])
@operation_id("create_instrument")
@validate(request=Instrument)
async def create_instrument(data: Instrument) -> ResponseReturnValue:
    """Create a new Instrument"""
    try:
        entity_data = data.model_dump(by_alias=True)
        response = await service.save(
            entity=entity_data,
            entity_class=Instrument.ENTITY_NAME,
            entity_version=str(Instrument.ENTITY_VERSION),
        )
        logger.info("Created Instrument with ID: %s", response.metadata.id)
        return _to_entity_dict(response.data), 201
    except Exception as e:
        logger.error("Error creating instrument: %s", str(e))
        return {"error": str(e)}, 500


@instruments_bp.route("/<entity_id>", methods=["GET"])
@tag(["instruments"])
@operation_id("get_instrument")
async def get_instrument(entity_id: str) -> ResponseReturnValue:
    """Get an Instrument by ID"""
    try:
        response = await service.get(
            entity_id=entity_id,
            entity_class=Instrument.ENTITY_NAME,
        )
        if is_not_found(response):
            return {"error": "Not found"}, 404
        return _to_entity_dict(response.data), 200
    except Exception as e:
        logger.error("Error getting instrument: %s", str(e))
        return {"error": str(e)}, 500


@instruments_bp.route("", methods=["GET"])
@tag(["instruments"])
@operation_id("list_instruments")
async def list_instruments() -> ResponseReturnValue:
    """List all Instruments"""
    try:
        response = await service.list(
            entity_class=Instrument.ENTITY_NAME,
        )
        return {"data": response.data}, 200
    except Exception as e:
        logger.error("Error listing instruments: %s", str(e))
        return {"error": str(e)}, 500

