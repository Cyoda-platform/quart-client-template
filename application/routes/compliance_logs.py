"""
Compliance log routes for institutional trading platform.

Provides REST API endpoints for audit trail and regulatory compliance.
"""

import logging
from typing import Any

from quart import Blueprint
from quart_schema import validate_request, validate_response

from application.entity.compliance_log.version_1.compliance_log import ComplianceLog
from services.services import get_entity_service

logger = logging.getLogger(__name__)

compliance_logs_bp = Blueprint(
    "compliance_logs", __name__, url_prefix="/api/compliance-logs"
)


class _ServiceProxy:
    """Lazy proxy to avoid initializing services at import time."""

    def __getattr__(self, name: str) -> Any:
        return getattr(get_entity_service(), name)


service = _ServiceProxy()


@compliance_logs_bp.post("")
@validate_request(ComplianceLog)
@validate_response(ComplianceLog, 201)
async def create_compliance_log(data: ComplianceLog) -> tuple[dict[str, Any], int]:
    """Create a new compliance log entry."""
    try:
        entity_data = data.model_dump(by_alias=True)
        response = await service.save(
            entity=entity_data,
            entity_class=ComplianceLog.ENTITY_NAME,
            entity_version=str(ComplianceLog.ENTITY_VERSION),
        )
        logger.info(f"Created compliance log: {response.metadata.id}")
        return response.data, 201
    except Exception as e:
        logger.error(f"Error creating compliance log: {str(e)}")
        return {"error": str(e)}, 400


@compliance_logs_bp.get("/<log_id>")
@validate_response(ComplianceLog, 200)
async def get_compliance_log(log_id: str) -> tuple[dict[str, Any], int]:
    """Get compliance log by ID."""
    try:
        response = await service.get(
            entity_id=log_id,
            entity_class=ComplianceLog.ENTITY_NAME,
        )
        return response.data, 200
    except Exception as e:
        logger.error(f"Error getting compliance log: {str(e)}")
        return {"error": str(e)}, 404


@compliance_logs_bp.put("/<log_id>")
@validate_request(ComplianceLog)
@validate_response(ComplianceLog, 200)
async def update_compliance_log(
    log_id: str, data: ComplianceLog
) -> tuple[dict[str, Any], int]:
    """Update a compliance log."""
    try:
        entity_data = data.model_dump(by_alias=True)
        response = await service.update(
            entity_id=log_id,
            entity=entity_data,
            entity_class=ComplianceLog.ENTITY_NAME,
        )
        logger.info(f"Updated compliance log: {log_id}")
        return response.data, 200
    except Exception as e:
        logger.error(f"Error updating compliance log: {str(e)}")
        return {"error": str(e)}, 400


@compliance_logs_bp.post("/<log_id>/transitions/<transition_name>")
async def transition_compliance_log(
    log_id: str, transition_name: str
) -> tuple[dict[str, Any], int]:
    """Trigger a workflow transition on a compliance log."""
    try:
        response = await service.transition(
            entity_id=log_id,
            transition_name=transition_name,
            entity_class=ComplianceLog.ENTITY_NAME,
        )
        logger.info(f"Transitioned compliance log {log_id} to {transition_name}")
        return response.data, 200
    except Exception as e:
        logger.error(f"Error transitioning compliance log: {str(e)}")
        return {"error": str(e)}, 400
