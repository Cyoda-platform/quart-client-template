"""
RiskProfile routes for institutional trading platform.
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from quart import Blueprint, jsonify, request
from quart.typing import ResponseReturnValue
from quart_schema import operation_id, tag, validate

from common.exception import is_not_found
from services.services import get_entity_service
from application.entity.risk_profile import RiskProfile

logger = logging.getLogger(__name__)

risk_profiles_bp = Blueprint("risk_profiles", __name__, url_prefix="/api/risk-profiles")


class _ServiceProxy:
    def __getattr__(self, name: str) -> Any:
        return getattr(get_entity_service(), name)


service = _ServiceProxy()


def _to_entity_dict(data: Dict[str, Any]) -> Dict[str, Any]:
    """Convert entity data to response format."""
    return data if isinstance(data, dict) else data.model_dump(by_alias=True)


@risk_profiles_bp.route("", methods=["POST"])
@tag(["risk-profiles"])
@operation_id("create_risk_profile")
@validate(request=RiskProfile)
async def create_risk_profile(data: RiskProfile) -> ResponseReturnValue:
    """Create a new RiskProfile"""
    try:
        entity_data = data.model_dump(by_alias=True)
        response = await service.save(
            entity=entity_data,
            entity_class=RiskProfile.ENTITY_NAME,
            entity_version=str(RiskProfile.ENTITY_VERSION),
        )
        logger.info("Created RiskProfile with ID: %s", response.metadata.id)
        return _to_entity_dict(response.data), 201
    except Exception as e:
        logger.error("Error creating risk profile: %s", str(e))
        return {"error": str(e)}, 500


@risk_profiles_bp.route("/<entity_id>", methods=["GET"])
@tag(["risk-profiles"])
@operation_id("get_risk_profile")
async def get_risk_profile(entity_id: str) -> ResponseReturnValue:
    """Get a RiskProfile by ID"""
    try:
        response = await service.get(
            entity_id=entity_id,
            entity_class=RiskProfile.ENTITY_NAME,
        )
        if is_not_found(response):
            return {"error": "Not found"}, 404
        return _to_entity_dict(response.data), 200
    except Exception as e:
        logger.error("Error getting risk profile: %s", str(e))
        return {"error": str(e)}, 500


@risk_profiles_bp.route("", methods=["GET"])
@tag(["risk-profiles"])
@operation_id("list_risk_profiles")
async def list_risk_profiles() -> ResponseReturnValue:
    """List all RiskProfiles"""
    try:
        response = await service.list(
            entity_class=RiskProfile.ENTITY_NAME,
        )
        return {"data": response.data}, 200
    except Exception as e:
        logger.error("Error listing risk profiles: %s", str(e))
        return {"error": str(e)}, 500

