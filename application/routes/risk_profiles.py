"""
RiskProfile management API routes for the trading platform.

Provides REST endpoints for RiskProfile CRUD operations.
"""

import logging
from typing import Any, Dict

from quart import Blueprint
from quart_schema import validate_request, validate_response

from application.entity.risk_profile.version_1.risk_profile import RiskProfile
from services.services import get_entity_service

logger = logging.getLogger(__name__)

risk_profiles_bp = Blueprint("risk_profiles", __name__, url_prefix="/api/risk_profiles")


@risk_profiles_bp.route("", methods=["POST"])
@validate_request(RiskProfile)
@validate_response(RiskProfile, status_code=201)
async def create_riskprofile(data: RiskProfile) -> tuple[Dict[str, Any], int]:
    """Create a new RiskProfile."""
    try:
        entity_service = get_entity_service()
        riskprofile_data = data.model_dump(by_alias=True)
        response = await entity_service.save(
            entity=riskprofile_data,
            entity_class=RiskProfile.ENTITY_NAME,
            entity_version=str(RiskProfile.ENTITY_VERSION),
        )
        riskprofile_data["id"] = response.metadata.id
        riskprofile_data["state"] = response.metadata.state
        logger.info(f"RiskProfile created: {response.metadata.id}")
        return riskprofile_data, 201
    except Exception as e:
        logger.error(f"Failed to create RiskProfile: {str(e)}")
        return {"error": str(e)}, 400


@risk_profiles_bp.route("/<riskprofile_id>", methods=["GET"])
async def get_riskprofile(riskprofile_id: str) -> tuple[Dict[str, Any], int]:
    """Get RiskProfile by technical ID."""
    try:
        entity_service = get_entity_service()
        response = await entity_service.get_by_id(
            entity_id=riskprofile_id,
            entity_class=RiskProfile.ENTITY_NAME,
            entity_version=str(RiskProfile.ENTITY_VERSION),
        )
        if response is None:
            return {"error": "RiskProfile not found"}, 404
        riskprofile_data = response.data.model_dump(by_alias=True)
        riskprofile_data["id"] = response.metadata.id
        riskprofile_data["state"] = response.metadata.state
        return riskprofile_data, 200
    except Exception as e:
        logger.error(f"Failed to get RiskProfile: {str(e)}")
        return {"error": str(e)}, 404


@risk_profiles_bp.route("/<riskprofile_id>", methods=["PUT"])
@validate_request(RiskProfile)
async def update_riskprofile(
    riskprofile_id: str, data: RiskProfile
) -> tuple[Dict[str, Any], int]:
    """Update a RiskProfile."""
    try:
        entity_service = get_entity_service()
        riskprofile_data = data.model_dump(by_alias=True)
        response = await entity_service.update(
            entity_id=riskprofile_id,
            entity=riskprofile_data,
            entity_class=RiskProfile.ENTITY_NAME,
            entity_version=str(RiskProfile.ENTITY_VERSION),
        )
        riskprofile_data["id"] = response.metadata.id
        riskprofile_data["state"] = response.metadata.state
        logger.info(f"RiskProfile updated: {riskprofile_id}")
        return riskprofile_data, 200
    except Exception as e:
        logger.error(f"Failed to update RiskProfile: {str(e)}")
        return {"error": str(e)}, 400


@risk_profiles_bp.route("/<riskprofile_id>", methods=["DELETE"])
async def delete_riskprofile(riskprofile_id: str) -> tuple[Dict[str, str], int]:
    """Delete a RiskProfile."""
    try:
        entity_service = get_entity_service()
        await entity_service.delete_by_id(
            entity_id=riskprofile_id,
            entity_class=RiskProfile.ENTITY_NAME,
            entity_version=str(RiskProfile.ENTITY_VERSION),
        )
        logger.info(f"RiskProfile deleted: {riskprofile_id}")
        return {"message": "RiskProfile deleted successfully"}, 200
    except Exception as e:
        logger.error(f"Failed to delete RiskProfile: {str(e)}")
        return {"error": str(e)}, 400
