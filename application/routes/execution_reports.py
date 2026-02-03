"""
ExecutionReport Routes for Institutional Trading Platform

Manages all ExecutionReport-related API endpoints.
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from quart import Blueprint
from quart.typing import ResponseReturnValue
from quart_schema import operation_id, tag, validate

from common.exception import is_not_found
from services.services import get_entity_service

from application.entity.execution_report.version_1.execution_report import ExecutionReport


class _ServiceProxy:
    def __getattr__(self, name: str) -> Any:
        return getattr(get_entity_service(), name)


service = _ServiceProxy()
logger = logging.getLogger(__name__)


def _to_entity_dict(data: Any) -> Dict[str, Any]:
    return data.model_dump(by_alias=True) if hasattr(data, "model_dump") else data


execution_reports_bp = Blueprint("execution_reports", __name__, url_prefix="/api/execution-reports")


@execution_reports_bp.route("", methods=["POST"])
@tag(["execution-reports"])
@operation_id("create_execution_report")
@validate(request=ExecutionReport, responses={201: (dict, None), 400: (dict, None), 500: (dict, None)})
async def create_execution_report(data: ExecutionReport) -> ResponseReturnValue:
    """Create a new execution report"""
    try:
        entity_data = data.model_dump(by_alias=True)
        response = await service.save(
            entity=entity_data,
            entity_class=ExecutionReport.ENTITY_NAME,
            entity_version=str(ExecutionReport.ENTITY_VERSION),
        )
        return _to_entity_dict(response.data), 201
    except Exception as e:
        logger.error(f"Error creating execution report: {str(e)}")
        return {"error": str(e)}, 500


@execution_reports_bp.route("/<entity_id>", methods=["GET"])
@tag(["execution-reports"])
@operation_id("get_execution_report")
@validate(responses={200: (dict, None), 404: (dict, None), 500: (dict, None)})
async def get_execution_report(entity_id: str) -> ResponseReturnValue:
    """Get an execution report by ID"""
    try:
        response = await service.get(
            entity_id=entity_id,
            entity_class=ExecutionReport.ENTITY_NAME,
            entity_version=str(ExecutionReport.ENTITY_VERSION),
        )
        if is_not_found(response):
            return {"error": "Execution report not found"}, 404
        return _to_entity_dict(response.data), 200
    except Exception as e:
        logger.error(f"Error getting execution report: {str(e)}")
        return {"error": str(e)}, 500


@execution_reports_bp.route("", methods=["GET"])
@tag(["execution-reports"])
@operation_id("list_execution_reports")
@validate(responses={200: (dict, None), 500: (dict, None)})
async def list_execution_reports() -> ResponseReturnValue:
    """List all execution reports"""
    try:
        response = await service.list(
            entity_class=ExecutionReport.ENTITY_NAME,
            entity_version=str(ExecutionReport.ENTITY_VERSION),
            limit=100,
            offset=0,
        )
        return {"executionReports": [_to_entity_dict(item) for item in response.data]}, 200
    except Exception as e:
        logger.error(f"Error listing execution reports: {str(e)}")
        return {"error": str(e)}, 500


@execution_reports_bp.route("/<entity_id>/transition", methods=["POST"])
@tag(["execution-reports"])
@operation_id("transition_execution_report")
@validate(request=dict, responses={200: (dict, None), 400: (dict, None), 500: (dict, None)})
async def transition_execution_report(entity_id: str, data: dict) -> ResponseReturnValue:
    """Trigger a workflow transition on an execution report"""
    try:
        transition_name = data.get("transitionName")
        if not transition_name:
            return {"error": "transitionName is required"}, 400

        response = await service.transition(
            entity_id=entity_id,
            entity_class=ExecutionReport.ENTITY_NAME,
            entity_version=str(ExecutionReport.ENTITY_VERSION),
            transition_name=transition_name,
        )
        return _to_entity_dict(response.data), 200
    except Exception as e:
        logger.error(f"Error transitioning execution report: {str(e)}")
        return {"error": str(e)}, 500

