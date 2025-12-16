"""
Instrument management API routes for the trading platform.

Provides REST endpoints for Instrument CRUD operations.
"""

import logging
from typing import Any, Dict

from quart import Blueprint
from quart_schema import validate_request, validate_response

from application.entity.instrument.version_1.instrument import Instrument
from services.services import get_entity_service

logger = logging.getLogger(__name__)

instruments_bp = Blueprint("instruments", __name__, url_prefix="/api/instruments")


@instruments_bp.route("", methods=["POST"])
@validate_request(Instrument)
@validate_response(Instrument, status_code=201)
async def create_instrument(data: Instrument) -> tuple[Dict[str, Any], int]:
    """Create a new Instrument."""
    try:
        entity_service = get_entity_service()
        instrument_data = data.model_dump(by_alias=True)
        response = await entity_service.save(
            entity=instrument_data,
            entity_class=Instrument.ENTITY_NAME,
            entity_version=str(Instrument.ENTITY_VERSION),
        )
        instrument_data["id"] = response.metadata.id
        instrument_data["state"] = response.metadata.state
        logger.info(f"Instrument created: {response.metadata.id}")
        return instrument_data, 201
    except Exception as e:
        logger.error(f"Failed to create Instrument: {str(e)}")
        return {"error": str(e)}, 400


@instruments_bp.route("/<instrument_id>", methods=["GET"])
async def get_instrument(instrument_id: str) -> tuple[Dict[str, Any], int]:
    """Get Instrument by technical ID."""
    try:
        entity_service = get_entity_service()
        response = await entity_service.get_by_id(
            entity_id=instrument_id,
            entity_class=Instrument.ENTITY_NAME,
            entity_version=str(Instrument.ENTITY_VERSION),
        )
        if response is None:
            return {"error": "Instrument not found"}, 404
        instrument_data = response.data.model_dump(by_alias=True)
        instrument_data["id"] = response.metadata.id
        instrument_data["state"] = response.metadata.state
        return instrument_data, 200
    except Exception as e:
        logger.error(f"Failed to get Instrument: {str(e)}")
        return {"error": str(e)}, 404


@instruments_bp.route("/<instrument_id>", methods=["PUT"])
@validate_request(Instrument)
async def update_instrument(
    instrument_id: str, data: Instrument
) -> tuple[Dict[str, Any], int]:
    """Update a Instrument."""
    try:
        entity_service = get_entity_service()
        instrument_data = data.model_dump(by_alias=True)
        response = await entity_service.update(
            entity_id=instrument_id,
            entity=instrument_data,
            entity_class=Instrument.ENTITY_NAME,
            entity_version=str(Instrument.ENTITY_VERSION),
        )
        instrument_data["id"] = response.metadata.id
        instrument_data["state"] = response.metadata.state
        logger.info(f"Instrument updated: {instrument_id}")
        return instrument_data, 200
    except Exception as e:
        logger.error(f"Failed to update Instrument: {str(e)}")
        return {"error": str(e)}, 400


@instruments_bp.route("/<instrument_id>", methods=["DELETE"])
async def delete_instrument(instrument_id: str) -> tuple[Dict[str, str], int]:
    """Delete a Instrument."""
    try:
        entity_service = get_entity_service()
        await entity_service.delete_by_id(
            entity_id=instrument_id,
            entity_class=Instrument.ENTITY_NAME,
            entity_version=str(Instrument.ENTITY_VERSION),
        )
        logger.info(f"Instrument deleted: {instrument_id}")
        return {"message": "Instrument deleted successfully"}, 200
    except Exception as e:
        logger.error(f"Failed to delete Instrument: {str(e)}")
        return {"error": str(e)}, 400
