"""
Compliance event management API routes for the trading platform.

Provides REST endpoints for compliance event CRUD operations.
"""

import logging
from typing import Any, Dict

from quart import Blueprint, jsonify, request
from quart_schema import validate_request, validate_response

from application.entity.compliance_event.version_1.compliance_event import (
    ComplianceEvent,
)
from services.services import get_entity_service

logger = logging.getLogger(__name__)

compliance_events_bp = Blueprint(
    "compliance_events", __name__, url_prefix="/api/compliance-events"
)


@compliance_events_bp.route("", methods=["POST"])
@validate_request(ComplianceEvent)
@validate_response(ComplianceEvent, status_code=201)
async def create_compliance_event(data: ComplianceEvent) -> tuple[Dict[str, Any], int]:
    """Create a new compliance event."""
    try:
        entity_service = get_entity_service()
        event_data = data.model_dump(by_alias=True)
        response = await entity_service.save(
            entity=event_data,
            entity_class=ComplianceEvent.ENTITY_NAME,
            entity_version=str(ComplianceEvent.ENTITY_VERSION),
        )
        event_data["id"] = response.metadata.id
        event_data["state"] = response.metadata.state
        logger.info(f"Compliance event created: {response.metadata.id}")
        return event_data, 201
    except Exception as e:
        logger.error(f"Failed to create compliance event: {str(e)}")
        return {"error": str(e)}, 400


@compliance_events_bp.route("/<event_id>", methods=["GET"])
async def get_compliance_event(event_id: str) -> tuple[Dict[str, Any], int]:
    """Get compliance event by technical ID."""
    try:
        entity_service = get_entity_service()
        response = await entity_service.get(
            entity_id=event_id,
            entity_class=ComplianceEvent.ENTITY_NAME,
            entity_version=str(ComplianceEvent.ENTITY_VERSION),
        )
        event_data = response.entity.model_dump(by_alias=True)
        event_data["id"] = response.metadata.id
        event_data["state"] = response.metadata.state
        return event_data, 200
    except Exception as e:
        logger.error(f"Failed to get compliance event: {str(e)}")
        return {"error": str(e)}, 404


@compliance_events_bp.route("/<event_id>", methods=["PUT"])
@validate_request(ComplianceEvent)
async def update_compliance_event(
    event_id: str, data: ComplianceEvent
) -> tuple[Dict[str, Any], int]:
    """Update a compliance event."""
    try:
        entity_service = get_entity_service()
        event_data = data.model_dump(by_alias=True)
        response = await entity_service.save(
            entity=event_data,
            entity_class=ComplianceEvent.ENTITY_NAME,
            entity_version=str(ComplianceEvent.ENTITY_VERSION),
        )
        event_data["id"] = response.metadata.id
        event_data["state"] = response.metadata.state
        logger.info(f"Compliance event updated: {event_id}")
        return event_data, 200
    except Exception as e:
        logger.error(f"Failed to update compliance event: {str(e)}")
        return {"error": str(e)}, 400


@compliance_events_bp.route("/<event_id>", methods=["DELETE"])
async def delete_compliance_event(event_id: str) -> tuple[Dict[str, str], int]:
    """Delete a compliance event."""
    try:
        entity_service = get_entity_service()
        await entity_service.delete(
            entity_id=event_id,
            entity_class=ComplianceEvent.ENTITY_NAME,
            entity_version=str(ComplianceEvent.ENTITY_VERSION),
        )
        logger.info(f"Compliance event deleted: {event_id}")
        return {"message": "Compliance event deleted successfully"}, 200
    except Exception as e:
        logger.error(f"Failed to delete compliance event: {str(e)}")
        return {"error": str(e)}, 400
