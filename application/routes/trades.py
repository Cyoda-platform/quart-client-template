"""
Trade management API routes for the trading platform.

Provides REST endpoints for trade CRUD operations and state transitions.
"""

import logging
from typing import Any, Dict

from quart import Blueprint, jsonify, request
from quart_schema import validate_request, validate_response

from application.entity.trade.version_1.trade import Trade
from services.services import get_entity_service

logger = logging.getLogger(__name__)

trades_bp = Blueprint("trades", __name__, url_prefix="/api/trades")


@trades_bp.route("", methods=["POST"])
@validate_request(Trade)
@validate_response(Trade, status_code=201)
async def create_trade(data: Trade) -> tuple[Dict[str, Any], int]:
    """
    Create a new trade.

    Args:
        data: Trade data

    Returns:
        Created trade with technical ID
    """
    try:
        entity_service = get_entity_service()

        trade_data = data.model_dump(by_alias=True)
        response = await entity_service.save(
            entity=trade_data,
            entity_class=Trade.ENTITY_NAME,
            entity_version=str(Trade.ENTITY_VERSION),
        )

        trade_data["id"] = response.metadata.id
        trade_data["state"] = response.metadata.state

        logger.info(f"Trade created: {response.metadata.id}")
        return trade_data, 201

    except Exception as e:
        logger.error(f"Failed to create trade: {str(e)}")
        return {"error": str(e)}, 400


@trades_bp.route("/<trade_id>", methods=["GET"])
async def get_trade(trade_id: str) -> tuple[Dict[str, Any], int]:
    """
    Get trade by technical ID.

    Args:
        trade_id: Technical ID of the trade

    Returns:
        Trade details
    """
    try:
        entity_service = get_entity_service()

        response = await entity_service.get(
            entity_id=trade_id,
            entity_class=Trade.ENTITY_NAME,
            entity_version=str(Trade.ENTITY_VERSION),
        )

        trade_data = response.entity.model_dump(by_alias=True)
        trade_data["id"] = response.metadata.id
        trade_data["state"] = response.metadata.state

        return trade_data, 200

    except Exception as e:
        logger.error(f"Failed to get trade: {str(e)}")
        return {"error": str(e)}, 404


@trades_bp.route("/<trade_id>", methods=["PUT"])
@validate_request(Trade)
async def update_trade(trade_id: str, data: Trade) -> tuple[Dict[str, Any], int]:
    """
    Update a trade.

    Args:
        trade_id: Technical ID of the trade
        data: Updated trade data

    Returns:
        Updated trade
    """
    try:
        entity_service = get_entity_service()

        trade_data = data.model_dump(by_alias=True)
        response = await entity_service.save(
            entity=trade_data,
            entity_class=Trade.ENTITY_NAME,
            entity_version=str(Trade.ENTITY_VERSION),
        )

        trade_data["id"] = response.metadata.id
        trade_data["state"] = response.metadata.state

        logger.info(f"Trade updated: {trade_id}")
        return trade_data, 200

    except Exception as e:
        logger.error(f"Failed to update trade: {str(e)}")
        return {"error": str(e)}, 400


@trades_bp.route("/<trade_id>", methods=["DELETE"])
async def delete_trade(trade_id: str) -> tuple[Dict[str, str], int]:
    """
    Delete a trade.

    Args:
        trade_id: Technical ID of the trade

    Returns:
        Deletion confirmation
    """
    try:
        entity_service = get_entity_service()

        await entity_service.delete(
            entity_id=trade_id,
            entity_class=Trade.ENTITY_NAME,
            entity_version=str(Trade.ENTITY_VERSION),
        )

        logger.info(f"Trade deleted: {trade_id}")
        return {"message": "Trade deleted successfully"}, 200

    except Exception as e:
        logger.error(f"Failed to delete trade: {str(e)}")
        return {"error": str(e)}, 400


@trades_bp.route("/<trade_id>/transition", methods=["POST"])
async def transition_trade(trade_id: str) -> tuple[Dict[str, Any], int]:
    """
    Transition trade to next state.

    Args:
        trade_id: Technical ID of the trade

    Returns:
        Updated trade with new state
    """
    try:
        entity_service = get_entity_service()
        body = await request.get_json()
        transition_name = body.get("transition")

        if not transition_name:
            return {"error": "Transition name is required"}, 400

        response = await entity_service.transition(
            entity_id=trade_id,
            entity_class=Trade.ENTITY_NAME,
            entity_version=str(Trade.ENTITY_VERSION),
            transition=transition_name,
        )

        trade_data = response.entity.model_dump(by_alias=True)
        trade_data["id"] = response.metadata.id
        trade_data["state"] = response.metadata.state

        logger.info(f"Trade {trade_id} transitioned to {response.metadata.state}")
        return trade_data, 200

    except Exception as e:
        logger.error(f"Failed to transition trade: {str(e)}")
        return {"error": str(e)}, 400

