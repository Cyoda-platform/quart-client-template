"""
ComplianceEvent management API routes for the trading platform.

Provides REST endpoints for ComplianceEvent CRUD operations.
"""

import logging
from typing import Any, Dict

from quart import Blueprint
from quart_schema import validate_request, validate_response

from application.entity.compliance_event.version_1.compliance_event import (
    ComplianceEvent,
)
from services.services import get_entity_service

logger = logging.getLogger(__name__)

compliance_events_bp = Blueprint(
    "compliance_events", __name__, url_prefix="/api/compliance_events"
)


@compliance_events_bp.route("", methods=["POST"])
@validate_request(ComplianceEvent)
@validate_response(ComplianceEvent, status_code=201)
async def create_complianceevent(data: ComplianceEvent) -> tuple[Dict[str, Any], int]:
    """Create a new ComplianceEvent."""
    try:
        entity_service = get_entity_service()
        complianceevent_data = data.model_dump(by_alias=True)
        response = await entity_service.save(
            entity=complianceevent_data,
            entity_class=ComplianceEvent.ENTITY_NAME,
            entity_version=str(ComplianceEvent.ENTITY_VERSION),
        )
        complianceevent_data["id"] = response.metadata.id
        complianceevent_data["state"] = response.metadata.state
        logger.info(f"ComplianceEvent created: {response.metadata.id}")
        return complianceevent_data, 201
    except Exception as e:
        logger.error(f"Failed to create ComplianceEvent: {str(e)}")
        return {"error": str(e)}, 400


@compliance_events_bp.route("/<complianceevent_id>", methods=["GET"])
async def get_complianceevent(complianceevent_id: str) -> tuple[Dict[str, Any], int]:
    """Get ComplianceEvent by technical ID."""
    try:
        entity_service = get_entity_service()
        response = await entity_service.get_by_id(
            entity_id=complianceevent_id,
            entity_class=ComplianceEvent.ENTITY_NAME,
            entity_version=str(ComplianceEvent.ENTITY_VERSION),
        )
        if response is None:
            return {"error": "ComplianceEvent not found"}, 404
        complianceevent_data = response.entity.model_dump(by_alias=True)
        complianceevent_data["id"] = response.metadata.id
        complianceevent_data["state"] = response.metadata.state
        return complianceevent_data, 200
    except Exception as e:
        logger.error(f"Failed to get ComplianceEvent: {str(e)}")
        return {"error": str(e)}, 404


@compliance_events_bp.route("/<complianceevent_id>", methods=["PUT"])
@validate_request(ComplianceEvent)
async def update_complianceevent(
    complianceevent_id: str, data: ComplianceEvent
) -> tuple[Dict[str, Any], int]:
    """Update a ComplianceEvent."""
    try:
        entity_service = get_entity_service()
        complianceevent_data = data.model_dump(by_alias=True)
        response = await entity_service.update(
            entity=complianceevent_data,
            entity_class=ComplianceEvent.ENTITY_NAME,
            entity_version=str(ComplianceEvent.ENTITY_VERSION),
        )
        complianceevent_data["id"] = response.metadata.id
        complianceevent_data["state"] = response.metadata.state
        logger.info(f"ComplianceEvent updated: {complianceevent_id}")
        return complianceevent_data, 200
    except Exception as e:
        logger.error(f"Failed to update ComplianceEvent: {str(e)}")
        return {"error": str(e)}, 400


@compliance_events_bp.route("/<complianceevent_id>", methods=["DELETE"])
async def delete_complianceevent(complianceevent_id: str) -> tuple[Dict[str, str], int]:
    """Delete a ComplianceEvent."""
    try:
        entity_service = get_entity_service()
        await entity_service.delete_by_id(
            entity_id=complianceevent_id,
            entity_class=ComplianceEvent.ENTITY_NAME,
            entity_version=str(ComplianceEvent.ENTITY_VERSION),
        )
        logger.info(f"ComplianceEvent deleted: {complianceevent_id}")
        return {"message": "ComplianceEvent deleted successfully"}, 200
    except Exception as e:
        logger.error(f"Failed to delete ComplianceEvent: {str(e)}")
        return {"error": str(e)}, 400
