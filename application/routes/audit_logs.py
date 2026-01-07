"""
Audit Log Routes for Enterprise Payment Processing System

Manages all AuditLog-related API endpoints.
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from quart import Blueprint, jsonify
from quart.typing import ResponseReturnValue
from quart_schema import operation_id, tag, validate

from services.services import get_entity_service
from application.entity.audit_log import AuditLog


class _ServiceProxy:
    def __getattr__(self, name: str) -> Any:
        return getattr(get_entity_service(), name)


service = _ServiceProxy()
logger = logging.getLogger(__name__)


def _to_entity_dict(data: Any) -> Dict[str, Any]:
    return data.model_dump(by_alias=True) if hasattr(data, "model_dump") else data


audit_logs_bp = Blueprint("audit_logs", __name__, url_prefix="/api/audit-logs")


@audit_logs_bp.route("", methods=["POST"])
@tag(["audit-logs"])
@operation_id("create_audit_log")
@validate(
    request=AuditLog,
    responses={
        201: (Dict[str, Any], None),
        400: (Dict[str, Any], None),
        500: (Dict[str, Any], None),
    },
)
async def create_audit_log(
    data: AuditLog,
) -> ResponseReturnValue:
    """Create a new AuditLog"""
    try:
        entity_data = data.model_dump(by_alias=True)
        response = await service.save(
            entity=entity_data,
            entity_class=AuditLog.ENTITY_NAME,
            entity_version=str(AuditLog.ENTITY_VERSION),
        )
        logger.info("Created AuditLog with ID: %s", response.metadata.id)
        return _to_entity_dict(response.data), 201

    except ValueError as e:
        logger.warning("Validation error creating AuditLog: %s", str(e))
        return {"error": str(e), "code": "VALIDATION_ERROR"}, 400
    except Exception as e:
        logger.exception("Error creating AuditLog: %s", str(e))
        return {"error": str(e), "code": "INTERNAL_ERROR"}, 500


@audit_logs_bp.route("/<entity_id>", methods=["GET"])
@tag(["audit-logs"])
@operation_id("get_audit_log")
@validate(
    responses={
        200: (Dict[str, Any], None),
        404: (Dict[str, Any], None),
        500: (Dict[str, Any], None),
    }
)
async def get_audit_log(entity_id: str) -> ResponseReturnValue:
    """Get AuditLog by ID"""
    try:
        if not entity_id or len(entity_id.strip()) == 0:
            return {"error": "Entity ID is required", "code": "INVALID_ID"}, 400

        response = await service.get_by_id(
            entity_id=entity_id,
            entity_class=AuditLog.ENTITY_NAME,
            entity_version=str(AuditLog.ENTITY_VERSION),
        )

        if not response:
            return {"error": "AuditLog not found", "code": "NOT_FOUND"}, 404

        return _to_entity_dict(response.data), 200

    except Exception as e:
        logger.exception("Error getting AuditLog %s: %s", entity_id, str(e))
        return {"error": str(e), "code": "INTERNAL_ERROR"}, 500


@audit_logs_bp.route("", methods=["GET"])
@tag(["audit-logs"])
@operation_id("list_audit_logs")
@validate(
    responses={
        200: (Dict[str, Any], None),
        500: (Dict[str, Any], None),
    }
)
async def list_audit_logs() -> ResponseReturnValue:
    """List all AuditLogs"""
    try:
        entities = await service.find_all(
            entity_class=AuditLog.ENTITY_NAME,
            entity_version=str(AuditLog.ENTITY_VERSION),
        )
        entity_list = [_to_entity_dict(r.data) for r in entities]
        return jsonify({"entities": entity_list, "total": len(entity_list)}), 200

    except Exception as e:
        logger.exception("Error listing AuditLogs: %s", str(e))
        return jsonify({"error": str(e)}), 500


@audit_logs_bp.route("/<entity_id>", methods=["GET"])
@tag(["audit-logs"])
@operation_id("get_audit_log_by_id")
@validate(
    responses={
        200: (Dict[str, Any], None),
        404: (Dict[str, Any], None),
        500: (Dict[str, Any], None),
    }
)
async def get_audit_log_details(entity_id: str) -> ResponseReturnValue:
    """Get detailed AuditLog information"""
    try:
        if not entity_id or len(entity_id.strip()) == 0:
            return {"error": "Entity ID is required", "code": "INVALID_ID"}, 400

        response = await service.get_by_id(
            entity_id=entity_id,
            entity_class=AuditLog.ENTITY_NAME,
            entity_version=str(AuditLog.ENTITY_VERSION),
        )

        if not response:
            return {"error": "AuditLog not found", "code": "NOT_FOUND"}, 404

        return _to_entity_dict(response.data), 200

    except Exception as e:
        logger.exception("Error getting AuditLog details %s: %s", entity_id, str(e))
        return {"error": str(e), "code": "INTERNAL_ERROR"}, 500
