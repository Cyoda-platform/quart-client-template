"""
Instrument management routes for institutional trading platform.

Provides REST API endpoints for instrument definitions and metadata.
"""

import logging
from typing import Any

from quart import Blueprint
from quart_schema import validate_request, validate_response

from application.entity.instrument.version_1.instrument import Instrument
from services.services import get_entity_service

logger = logging.getLogger(__name__)

instruments_bp = Blueprint("instruments", __name__, url_prefix="/api/instruments")


class _ServiceProxy:
    """Lazy proxy to avoid initializing services at import time."""

    def __getattr__(self, name: str) -> Any:
        return getattr(get_entity_service(), name)


service = _ServiceProxy()


@instruments_bp.post("")
@validate_request(Instrument)
@validate_response(Instrument, 201)
async def create_instrument(data: Instrument) -> tuple[dict[str, Any], int]:
    """Create a new instrument."""
    try:
        entity_data = data.model_dump(by_alias=True)
        response = await service.save(
            entity=entity_data,
            entity_class=Instrument.ENTITY_NAME,
            entity_version=str(Instrument.ENTITY_VERSION),
        )
        logger.info(f"Created instrument: {response.metadata.id}")
        return response.data, 201
    except Exception as e:
        logger.error(f"Error creating instrument: {str(e)}")
        return {"error": str(e)}, 400


@instruments_bp.get("/<instrument_id>")
@validate_response(Instrument, 200)
async def get_instrument(instrument_id: str) -> tuple[dict[str, Any], int]:
    """Get instrument by ID."""
    try:
        response = await service.get(
            entity_id=instrument_id,
            entity_class=Instrument.ENTITY_NAME,
        )
        return response.data, 200
    except Exception as e:
        logger.error(f"Error getting instrument: {str(e)}")
        return {"error": str(e)}, 404


@instruments_bp.put("/<instrument_id>")
@validate_request(Instrument)
@validate_response(Instrument, 200)
async def update_instrument(
    instrument_id: str, data: Instrument
) -> tuple[dict[str, Any], int]:
    """Update an instrument."""
    try:
        entity_data = data.model_dump(by_alias=True)
        response = await service.update(
            entity_id=instrument_id,
            entity=entity_data,
            entity_class=Instrument.ENTITY_NAME,
        )
        logger.info(f"Updated instrument: {instrument_id}")
        return response.data, 200
    except Exception as e:
        logger.error(f"Error updating instrument: {str(e)}")
        return {"error": str(e)}, 400
