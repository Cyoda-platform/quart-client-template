import logging
from typing import Any, Dict

from quart import Blueprint, request
from quart.typing import ResponseReturnValue
from quart_schema import operation_id, tag, validate

from application.entity.credit_report.version_1.credit_report import CreditReport
from application.models import ErrorResponse, EntityResponse
from common.utils.serialization import safe_serialize
from services.services import get_entity_service

logger = logging.getLogger(__name__)


class _ServiceProxy:
    def __getattr__(self, name: str) -> Any:
        return getattr(get_entity_service(), name)


service = _ServiceProxy()


def _to_entity_dict(data: Any) -> Dict[str, Any]:
    if data is None:
        raise ValueError("Cannot serialize None entity to dictionary")
    return data.model_dump(by_alias=True) if hasattr(data, "model_dump") else data


credit_reports_bp = Blueprint(
    "credit_reports", __name__, url_prefix="/api/credit-reports"
)


@credit_reports_bp.route("", methods=["POST"])
@tag(["credit-reports"])
@operation_id("create_credit_report")
@validate(responses={201: (EntityResponse, None), 400: (ErrorResponse, None), 500: (ErrorResponse, None)})
async def create_credit_report(data: CreditReport) -> ResponseReturnValue:
    try:
        if data is None:
            logger.warning("Create credit report called with None payload")
            return {"error": "Request body is required"}, 400

        entity_data = data.model_dump(by_alias=True)
        response = await service.save(
            entity=entity_data,
            entity_class=CreditReport.ENTITY_NAME,
            entity_version=str(CreditReport.ENTITY_VERSION),
        )
        logger.info("Created CreditReport with ID: %s", response.metadata.id)
        return _to_entity_dict(response.data), 201
    except ValueError as e:
        logger.warning("Validation error: %s", str(e))
        return {"error": str(e)}, 400
    except Exception as e:
        logger.exception("Error creating credit report: %s", str(e))
        return {"error": str(e)}, 500


@credit_reports_bp.route("/<entity_id>", methods=["GET"])
@tag(["credit-reports"])
@operation_id("get_credit_report")
@validate(responses={200: (EntityResponse, None), 404: (ErrorResponse, None), 500: (ErrorResponse, None)})
async def get_credit_report(entity_id: str) -> ResponseReturnValue:
    try:
        if not entity_id or len(entity_id.strip()) == 0:
            return {"error": "Entity ID is required"}, 400

        response = await service.get_by_id(
            entity_id=entity_id,
            entity_class=CreditReport.ENTITY_NAME,
            entity_version=str(CreditReport.ENTITY_VERSION),
        )

        if not response:
            return {"error": "CreditReport not found"}, 404

        return safe_serialize(response.data)
    except Exception as e:
        logger.exception("Error getting credit report: %s", str(e))
        return {"error": str(e)}, 500


@credit_reports_bp.route("/<entity_id>", methods=["PUT"])
@tag(["credit-reports"])
@operation_id("update_credit_report")
@validate(responses={200: (EntityResponse, None), 404: (ErrorResponse, None), 500: (ErrorResponse, None)})
async def update_credit_report(
    entity_id: str, data: CreditReport
) -> ResponseReturnValue:
    try:
        if data is None:
            logger.warning("Update credit report called with None payload")
            return {"error": "Request body is required"}, 400

        entity_data = data.model_dump(by_alias=True)
        response = await service.update(
            entity_id=entity_id,
            entity=entity_data,
            entity_class=CreditReport.ENTITY_NAME,
            entity_version=str(CreditReport.ENTITY_VERSION),
        )

        if not response:
            return {"error": "CreditReport not found"}, 404

        return _to_entity_dict(response.data), 200
    except Exception as e:
        logger.exception("Error updating credit report: %s", str(e))
        return {"error": str(e)}, 500


@credit_reports_bp.route("/<entity_id>/transition", methods=["POST"])
@tag(["credit-reports"])
@operation_id("trigger_credit_report_transition")
@validate(responses={200: (EntityResponse, None), 404: (ErrorResponse, None), 500: (ErrorResponse, None)})
async def trigger_transition(entity_id: str) -> ResponseReturnValue:
    try:
        data = await request.get_json()
        transition_name = data.get("transition_name")

        if not transition_name:
            return {"error": "transition_name is required"}, 400

        response = await service.execute_transition(
            entity_id=entity_id,
            transition=transition_name,
            entity_class=CreditReport.ENTITY_NAME,
            entity_version=str(CreditReport.ENTITY_VERSION),
        )

        return _to_entity_dict(response.data), 200
    except Exception as e:
        logger.exception("Error triggering transition: %s", str(e))
        return {"error": str(e)}, 500
