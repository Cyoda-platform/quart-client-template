"""
Instrument Routes for Trading Platform

Manages all Instrument-related API endpoints including instrument
registration, activation, and trading eligibility.
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from quart import Blueprint, jsonify, request
from quart.typing import ResponseReturnValue
from quart_schema import operation_id, tag

from common.service.entity_service import SearchConditionRequest
from services.services import get_entity_service
from application.entity.instrument.version_1.instrument import Instrument

logger = logging.getLogger(__name__)

# Service proxy
class _ServiceProxy:
    def __getattr__(self, name: str) -> Any:
        return getattr(get_entity_service(), name)

service = _ServiceProxy()

def _to_entity_dict(data: Any) -> Dict[str, Any]:
    return data.model_dump(by_alias=True) if hasattr(data, "model_dump") else data

instruments_bp = Blueprint("instruments", __name__, url_prefix="/api/instruments")

@instruments_bp.route("", methods=["POST"])
@tag(["instruments"])
@operation_id("register_instrument")
async def register_instrument() -> ResponseReturnValue:
    """Register a new instrument"""
    try:
        data = await request.get_json()
        
        # Create Instrument entity
        instrument = Instrument(**data)
        entity_data = instrument.model_dump(by_alias=True)

        # Save the instrument
        response = await service.save(
            entity=entity_data,
            entity_class=Instrument.ENTITY_NAME,
            entity_version=str(Instrument.ENTITY_VERSION),
        )

        logger.info("Registered Instrument with ID: %s", response.metadata.id)
        return _to_entity_dict(response.data), 201

    except ValueError as e:
        logger.warning("Validation error registering instrument: %s", str(e))
        return {"error": str(e), "code": "VALIDATION_ERROR"}, 400
    except Exception as e:
        logger.exception("Error registering instrument: %s", str(e))
        return {"error": str(e), "code": "INTERNAL_ERROR"}, 500

@instruments_bp.route("/<instrument_id>", methods=["GET"])
@tag(["instruments"])
@operation_id("get_instrument")
async def get_instrument(instrument_id: str) -> ResponseReturnValue:
    """Get instrument by ID"""
    try:
        response = await service.get_by_id(
            entity_id=instrument_id,
            entity_class=Instrument.ENTITY_NAME,
            entity_version=str(Instrument.ENTITY_VERSION),
        )

        if not response:
            return {"error": "Instrument not found", "code": "NOT_FOUND"}, 404

        return _to_entity_dict(response.data), 200

    except Exception as e:
        logger.exception("Error getting instrument %s: %s", instrument_id, str(e))
        return {"error": str(e), "code": "INTERNAL_ERROR"}, 500

@instruments_bp.route("/by-symbol/<symbol>", methods=["GET"])
@tag(["instruments"])
@operation_id("get_instrument_by_symbol")
async def get_instrument_by_symbol(symbol: str) -> ResponseReturnValue:
    """Get instrument by symbol"""
    try:
        builder = SearchConditionRequest.builder()
        builder.equals("symbol", symbol)
        condition = builder.build()

        entities = await service.search(
            entity_class=Instrument.ENTITY_NAME,
            condition=condition,
            entity_version=str(Instrument.ENTITY_VERSION),
        )

        if not entities:
            return {"error": "Instrument not found", "code": "NOT_FOUND"}, 404

        # Return first match
        return _to_entity_dict(entities[0].data), 200

    except Exception as e:
        logger.exception("Error getting instrument by symbol %s: %s", symbol, str(e))
        return {"error": str(e)}, 500

@instruments_bp.route("", methods=["GET"])
@tag(["instruments"])
@operation_id("list_instruments")
async def list_instruments() -> ResponseReturnValue:
    """List instruments with optional filtering"""
    try:
        # Get query parameters
        asset_class = request.args.get("assetClass")
        instrument_type = request.args.get("instrumentType")
        exchange = request.args.get("exchange")
        currency = request.args.get("currency")
        is_active = request.args.get("isActive")

        # Build search conditions
        search_conditions = {}
        if asset_class:
            search_conditions["assetClass"] = asset_class
        if instrument_type:
            search_conditions["instrumentType"] = instrument_type
        if exchange:
            search_conditions["exchange"] = exchange
        if currency:
            search_conditions["currency"] = currency
        if is_active is not None:
            search_conditions["isActive"] = is_active.lower()

        if search_conditions:
            builder = SearchConditionRequest.builder()
            for field, value in search_conditions.items():
                builder.equals(field, value)
            condition = builder.build()

            entities = await service.search(
                entity_class=Instrument.ENTITY_NAME,
                condition=condition,
                entity_version=str(Instrument.ENTITY_VERSION),
            )
        else:
            entities = await service.find_all(
                entity_class=Instrument.ENTITY_NAME,
                entity_version=str(Instrument.ENTITY_VERSION),
            )

        entity_list = [_to_entity_dict(r.data) for r in entities]
        return {"instruments": entity_list, "total": len(entity_list)}, 200

    except Exception as e:
        logger.exception("Error listing instruments: %s", str(e))
        return {"error": str(e)}, 500

@instruments_bp.route("/<instrument_id>/activate", methods=["POST"])
@tag(["instruments"])
@operation_id("activate_instrument")
async def activate_instrument(instrument_id: str) -> ResponseReturnValue:
    """Activate an instrument for trading"""
    try:
        response = await service.execute_transition(
            entity_id=instrument_id,
            transition="activate",
            entity_class=Instrument.ENTITY_NAME,
            entity_version=str(Instrument.ENTITY_VERSION),
        )

        logger.info("Activated instrument %s", instrument_id)
        return {
            "id": response.metadata.id,
            "message": "Instrument activated successfully",
            "newState": response.metadata.state,
        }, 200

    except Exception as e:
        logger.exception("Error activating instrument %s: %s", instrument_id, str(e))
        return {"error": str(e)}, 500

@instruments_bp.route("/<instrument_id>/deactivate", methods=["POST"])
@tag(["instruments"])
@operation_id("deactivate_instrument")
async def deactivate_instrument(instrument_id: str) -> ResponseReturnValue:
    """Deactivate an instrument"""
    try:
        response = await service.execute_transition(
            entity_id=instrument_id,
            transition="deactivate",
            entity_class=Instrument.ENTITY_NAME,
            entity_version=str(Instrument.ENTITY_VERSION),
        )

        logger.info("Deactivated instrument %s", instrument_id)
        return {
            "id": response.metadata.id,
            "message": "Instrument deactivated successfully",
            "newState": response.metadata.state,
        }, 200

    except Exception as e:
        logger.exception("Error deactivating instrument %s: %s", instrument_id, str(e))
        return {"error": str(e)}, 500
