"""
AuditEvent Routes for Cyoda Trading Platform

Manages all AuditEvent-related API endpoints including CRUD operations
for audit trail events and compliance tracking.
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from quart import Blueprint, jsonify, request
from quart.typing import ResponseReturnValue

from services.services import get_entity_service

# Imported for entity constants / typing
from ..entity.audit_event import AuditEvent  # noqa: F401


# Module-level service instance to avoid repeated lookups
class _ServiceProxy:
    def __getattr__(self, name: str) -> Any:
        return getattr(get_entity_service(), name)


service = _ServiceProxy()

logger = logging.getLogger(__name__)


# Helper to normalize entity data from service (Pydantic model or dict)
def _to_entity_dict(data: Any) -> Dict[str, Any]:
    return data.model_dump(by_alias=True) if hasattr(data, "model_dump") else data


audit_events_bp = Blueprint(
    "audit_events", __name__, url_prefix="/api/audit-events"
)


# ---- Routes -----------------------------------------------------------------


@audit_events_bp.route("", methods=["POST"])
async def create_audit_event() -> ResponseReturnValue:
    """Create a new AuditEvent with comprehensive validation"""
    try:
        # Get JSON data from request
        data = await request.get_json()

        # Save the entity
        response = await service.save(
            entity=data,
            entity_class=AuditEvent.ENTITY_NAME,
            entity_version=str(AuditEvent.ENTITY_VERSION),
        )

        logger.info("Created AuditEvent with ID: %s", response.metadata.id)

        # Return created entity directly (thin proxy)
        return _to_entity_dict(response.data), 201

    except ValueError as e:
        logger.warning("Validation error creating AuditEvent: %s", str(e))
        return {"error": str(e), "code": "VALIDATION_ERROR"}, 400
    except Exception as e:  # pragma: no cover
        logger.exception("Error creating AuditEvent: %s", str(e))
        return {"error": str(e), "code": "INTERNAL_ERROR"}, 500


@audit_events_bp.route("/<entity_id>", methods=["GET"])
async def get_audit_event(entity_id: str) -> ResponseReturnValue:
    """Get AuditEvent by ID with validation"""
    try:
        # Validate entity ID format
        if not entity_id or len(entity_id.strip()) == 0:
            return (
                jsonify({"error": "Entity ID is required", "code": "INVALID_ID"}),
                400,
            )

        response = await service.get_by_id(
            entity_id=entity_id,
            entity_class=AuditEvent.ENTITY_NAME,
            entity_version=str(AuditEvent.ENTITY_VERSION),
        )

        if not response:
            return {"error": "AuditEvent not found", "code": "NOT_FOUND"}, 404

        # Thin proxy: return the entity directly
        return _to_entity_dict(response.data), 200

    except ValueError as e:
        logger.warning("Invalid entity ID %s: %s", entity_id, str(e))
        return {"error": str(e), "code": "INVALID_ID"}, 400
    except Exception as e:  # pragma: no cover
        logger.exception("Error getting AuditEvent %s: %s", entity_id, str(e))
        return {"error": str(e), "code": "INTERNAL_ERROR"}, 500


@audit_events_bp.route("", methods=["GET"])
async def list_audit_events() -> ResponseReturnValue:
    """List AuditEvents with optional filtering and validation"""
    try:
        # Get optional pagination parameters
        offset = int(request.args.get("offset", 0))
        limit = int(request.args.get("limit", 100))

        # Get entities
        entities = await service.find_all(
            entity_class=AuditEvent.ENTITY_NAME,
            entity_version=str(AuditEvent.ENTITY_VERSION),
        )

        # Thin proxy: return entities directly
        entity_list = [_to_entity_dict(r.data) for r in entities]

        # Apply pagination
        start = offset
        end = start + limit
        paginated_entities = entity_list[start:end]

        return jsonify({"entities": paginated_entities, "total": len(entity_list)}), 200

    except Exception as e:  # pragma: no cover
        logger.exception("Error listing AuditEvents: %s", str(e))
        return jsonify({"error": str(e)}), 500


@audit_events_bp.route("/<entity_id>", methods=["PUT"])
async def update_audit_event(entity_id: str) -> ResponseReturnValue:
    """Update AuditEvent and optionally trigger workflow transition with validation"""
    try:
        # Validate entity ID format
        if not entity_id or len(entity_id.strip()) == 0:
            return (
                jsonify({"error": "Entity ID is required", "code": "INVALID_ID"}),
                400,
            )

        # Get transition from query parameters
        transition = request.args.get("transition")

        # Get JSON data from request
        data = await request.get_json()

        # Update the entity
        response = await service.update(
            entity_id=entity_id,
            entity=data,
            entity_class=AuditEvent.ENTITY_NAME,
            transition=transition,
            entity_version=str(AuditEvent.ENTITY_VERSION),
        )

        logger.info("Updated AuditEvent %s", entity_id)

        # Return updated entity directly (thin proxy)
        return jsonify(_to_entity_dict(response.data)), 200

    except ValueError as e:
        logger.warning(
            "Validation error updating AuditEvent %s: %s", entity_id, str(e)
        )
        return jsonify({"error": str(e), "code": "VALIDATION_ERROR"}), 400
    except Exception as e:  # pragma: no cover
        logger.exception("Error updating AuditEvent %s: %s", entity_id, str(e))
        return jsonify({"error": str(e), "code": "INTERNAL_ERROR"}), 500


@audit_events_bp.route("/<entity_id>", methods=["DELETE"])
async def delete_audit_event(entity_id: str) -> ResponseReturnValue:
    """Delete AuditEvent with validation"""
    try:
        # Validate entity ID format
        if not entity_id or len(entity_id.strip()) == 0:
            return (
                jsonify({"error": "Entity ID is required", "code": "INVALID_ID"}),
                400,
            )

        await service.delete_by_id(
            entity_id=entity_id,
            entity_class=AuditEvent.ENTITY_NAME,
            entity_version=str(AuditEvent.ENTITY_VERSION),
        )

        logger.info("Deleted AuditEvent %s", entity_id)

        # Thin proxy: return success message
        return jsonify({
            "success": True,
            "message": "AuditEvent deleted successfully",
            "entity_id": entity_id,
        }), 200

    except ValueError as e:
        logger.warning("Invalid entity ID %s: %s", entity_id, str(e))
        return {"error": str(e), "code": "INVALID_ID"}, 400
    except Exception as e:  # pragma: no cover
        logger.exception("Error deleting AuditEvent %s: %s", entity_id, str(e))
        return {"error": str(e), "code": "INTERNAL_ERROR"}, 500
