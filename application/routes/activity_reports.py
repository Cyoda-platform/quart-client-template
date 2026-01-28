"""
Activity Reports API routes for Activity Tracker application.

Provides CRUD operations and workflow transitions for ActivityReport entities.
"""

import logging
from typing import Any, Dict, Tuple

from quart import Blueprint
from quart_schema import validate

from application.entity.activity_report.version_1.activity_report import (
    ActivityReport,
)
from services.services import get_entity_service

logger = logging.getLogger(__name__)

activity_reports_bp = Blueprint(
    "activity_reports", __name__, url_prefix="/api/activity-reports"
)


class _ServiceProxy:
    """Lazy proxy to avoid initializing services at import time."""

    def __getattr__(self, name: str) -> Any:
        return getattr(get_entity_service(), name)


service = _ServiceProxy()


def _to_entity_dict(data: Any) -> Dict[str, Any]:
    """Convert entity response to dictionary."""
    if isinstance(data, dict):
        return data
    if hasattr(data, "model_dump"):
        return data.model_dump(by_alias=True)
    return data


@activity_reports_bp.route("", methods=["POST"])
@validate(
    request=ActivityReport,
    responses={
        201: (Dict[str, Any], None),
        400: (Dict[str, str], None),
        500: (Dict[str, str], None),
    },
)
async def create_activity_report(data: ActivityReport) -> Tuple[Dict[str, Any], int]:
    """Create a new ActivityReport."""
    try:
        entity_data = data.model_dump(by_alias=True)

        response = await service.save(
            entity=entity_data,
            entity_class=ActivityReport.ENTITY_NAME,
            entity_version=str(ActivityReport.ENTITY_VERSION),
        )

        logger.info("Created ActivityReport with ID: %s", response.metadata.id)
        return _to_entity_dict(response.data), 201

    except Exception as e:
        logger.exception("Error creating ActivityReport: %s", str(e))
        return {"error": str(e)}, 500


@activity_reports_bp.route("/<entity_id>", methods=["GET"])
async def get_activity_report(entity_id: str) -> Tuple[Dict[str, Any], int]:
    """Get an ActivityReport by ID."""
    try:
        response = await service.find_by_id(
            entity_id=entity_id,
            entity_class=ActivityReport.ENTITY_NAME,
            entity_version=str(ActivityReport.ENTITY_VERSION),
        )

        if not response:
            return {"error": "ActivityReport not found"}, 404

        return _to_entity_dict(response.data), 200

    except Exception as e:
        logger.exception("Error retrieving ActivityReport %s: %s", entity_id, str(e))
        return {"error": str(e)}, 500


@activity_reports_bp.route("", methods=["GET"])
async def list_activity_reports() -> Tuple[Dict[str, Any], int]:
    """List all ActivityReports."""
    try:
        results = await service.find_all(
            entity_class=ActivityReport.ENTITY_NAME,
            entity_version=str(ActivityReport.ENTITY_VERSION),
        )

        entities = [_to_entity_dict(r.data) for r in results]
        return {"entities": entities, "total": len(entities)}, 200

    except Exception as e:
        logger.exception("Error listing ActivityReports: %s", str(e))
        return {"error": str(e)}, 500


@activity_reports_bp.route("/<entity_id>", methods=["PUT"])
@validate(
    request=ActivityReport,
    responses={
        200: (Dict[str, Any], None),
        404: (Dict[str, str], None),
        500: (Dict[str, str], None),
    },
)
async def update_activity_report(
    entity_id: str, data: ActivityReport
) -> Tuple[Dict[str, Any], int]:
    """Update an ActivityReport."""
    try:
        entity_data = data.model_dump(by_alias=True)

        response = await service.update(
            entity_id=entity_id,
            entity=entity_data,
            entity_class=ActivityReport.ENTITY_NAME,
            entity_version=str(ActivityReport.ENTITY_VERSION),
        )

        if not response:
            return {"error": "ActivityReport not found"}, 404

        logger.info("Updated ActivityReport with ID: %s", entity_id)
        return _to_entity_dict(response.data), 200

    except Exception as e:
        logger.exception("Error updating ActivityReport %s: %s", entity_id, str(e))
        return {"error": str(e)}, 500


@activity_reports_bp.route("/<entity_id>", methods=["DELETE"])
async def delete_activity_report(entity_id: str) -> Tuple[Dict[str, str], int]:
    """Delete an ActivityReport."""
    try:
        await service.delete(
            entity_id=entity_id,
            entity_class=ActivityReport.ENTITY_NAME,
            entity_version=str(ActivityReport.ENTITY_VERSION),
        )

        logger.info("Deleted ActivityReport with ID: %s", entity_id)
        return {"message": "ActivityReport deleted successfully"}, 200

    except Exception as e:
        logger.exception("Error deleting ActivityReport %s: %s", entity_id, str(e))
        return {"error": str(e)}, 500


@activity_reports_bp.route("/<entity_id>/transitions", methods=["GET"])
async def get_transitions(entity_id: str) -> Tuple[Dict[str, Any], int]:
    """Get available transitions for an ActivityReport."""
    try:
        transitions = await service.get_transitions(
            entity_id=entity_id,
            entity_class=ActivityReport.ENTITY_NAME,
            entity_version=str(ActivityReport.ENTITY_VERSION),
        )

        return {"transitions": transitions}, 200

    except Exception as e:
        logger.exception(
            "Error getting transitions for ActivityReport %s: %s", entity_id, str(e)
        )
        return {"error": str(e)}, 500


@activity_reports_bp.route(
    "/<entity_id>/transition/<transition_name>", methods=["POST"]
)
async def trigger_transition(
    entity_id: str, transition_name: str
) -> Tuple[Dict[str, Any], int]:
    """Trigger a workflow transition for an ActivityReport."""
    try:
        response = await service.execute_transition(
            entity_id=entity_id,
            transition=transition_name,
            entity_class=ActivityReport.ENTITY_NAME,
            entity_version=str(ActivityReport.ENTITY_VERSION),
        )

        logger.info(
            "Triggered transition %s for ActivityReport %s",
            transition_name,
            entity_id,
        )
        return _to_entity_dict(response.data), 200

    except Exception as e:
        logger.exception(
            "Error triggering transition for ActivityReport %s: %s",
            entity_id,
            str(e),
        )
        return {"error": str(e)}, 500
