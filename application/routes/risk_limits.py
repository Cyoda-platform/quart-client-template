"""
RiskLimit Routes for Trading Platform

Manages all RiskLimit-related API endpoints.
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from quart import Blueprint
from quart.typing import ResponseReturnValue
from quart_schema import operation_id, tag, validate

from common.exception import is_not_found
from services.services import get_entity_service
from application.entity.risk_limit.version_1.risk_limit import RiskLimit

logger = logging.getLogger(__name__)


class _ServiceProxy:
    def __getattr__(self, name: str) -> Any:
        return getattr(get_entity_service(), name)


service = _ServiceProxy()


def _to_entity_dict(data: Any) -> Dict[str, Any]:
    return data.model_dump(by_alias=True) if hasattr(data, "model_dump") else data


risk_limits_bp = Blueprint("risk_limits", __name__, url_prefix="/api/risk-limits")


@risk_limits_bp.route("", methods=["POST"])
@tag(["risk-limits"])
@operation_id("create_risk_limit")
@validate(request=RiskLimit, responses={201: (dict, None), 400: (dict, None), 500: (dict, None)})
async def create_risk_limit(data: RiskLimit) -> ResponseReturnValue:
    """Create a new risk limit"""
    try:
        entity_data = data.model_dump(by_alias=True)
        response = await service.save(
            entity=entity_data,
            entity_class=RiskLimit.ENTITY_NAME,
            entity_version=str(RiskLimit.ENTITY_VERSION),
        )
        logger.info(f"Created risk limit with ID: {response.metadata.id}")
        return _to_entity_dict(response.data), 201
    except Exception as e:
        logger.error(f"Error creating risk limit: {str(e)}")
        return {"error": str(e)}, 500


@risk_limits_bp.route("/<entity_id>", methods=["GET"])
@tag(["risk-limits"])
@operation_id("get_risk_limit")
@validate(responses={200: (dict, None), 404: (dict, None), 500: (dict, None)})
async def get_risk_limit(entity_id: str) -> ResponseReturnValue:
    """Get a risk limit by ID"""
    try:
        response = await service.get(
            entity_id=entity_id,
            entity_class=RiskLimit.ENTITY_NAME,
        )
        if is_not_found(response):
            return {"error": "Risk limit not found"}, 404
        return _to_entity_dict(response.data), 200
    except Exception as e:
        logger.error(f"Error getting risk limit: {str(e)}")
        return {"error": str(e)}, 500


@risk_limits_bp.route("", methods=["GET"])
@tag(["risk-limits"])
@operation_id("list_risk_limits")
@validate(responses={200: (dict, None), 500: (dict, None)})
async def list_risk_limits() -> ResponseReturnValue:
    """List all risk limits"""
    try:
        response = await service.list(
            entity_class=RiskLimit.ENTITY_NAME,
            limit=100,
            offset=0,
        )
        limits = [_to_entity_dict(item) for item in response.data]
        return {"limits": limits, "total": len(limits)}, 200
    except Exception as e:
        logger.error(f"Error listing risk limits: {str(e)}")
        return {"error": str(e)}, 500

