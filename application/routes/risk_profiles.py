"""
Risk profile management API routes for the trading platform.

Provides REST endpoints for risk profile CRUD operations.
"""

import logging
from typing import Any, Dict

from quart import Blueprint, jsonify, request
from quart_schema import validate_request, validate_response

from application.entity.risk_profile.version_1.risk_profile import RiskProfile
from services.services import get_entity_service

logger = logging.getLogger(__name__)

risk_profiles_bp = Blueprint("risk_profiles", __name__, url_prefix="/api/risk-profiles")


@risk_profiles_bp.route("", methods=["POST"])
@validate_request(RiskProfile)
@validate_response(RiskProfile, status_code=201)
async def create_risk_profile(data: RiskProfile) -> tuple[Dict[str, Any], int]:
    """
    Create a new risk profile.

    Args:
        data: RiskProfile data

    Returns:
        Created risk profile with technical ID
    """
    try:
        entity_service = get_entity_service()

        risk_profile_data = data.model_dump(by_alias=True)
        response = await entity_service.save(
            entity=risk_profile_data,
            entity_class=RiskProfile.ENTITY_NAME,
            entity_version=str(RiskProfile.ENTITY_VERSION),
        )

        risk_profile_data["id"] = response.metadata.id
        risk_profile_data["state"] = response.metadata.state

        logger.info(f"Risk profile created: {response.metadata.id}")
        return risk_profile_data, 201

    except Exception as e:
        logger.error(f"Failed to create risk profile: {str(e)}")
        return {"error": str(e)}, 400


@risk_profiles_bp.route("/<risk_profile_id>", methods=["GET"])
async def get_risk_profile(risk_profile_id: str) -> tuple[Dict[str, Any], int]:
    """
    Get risk profile by technical ID.

    Args:
        risk_profile_id: Technical ID of the risk profile

    Returns:
        Risk profile details
    """
    try:
        entity_service = get_entity_service()

        response = await entity_service.get(
            entity_id=risk_profile_id,
            entity_class=RiskProfile.ENTITY_NAME,
            entity_version=str(RiskProfile.ENTITY_VERSION),
        )

        risk_profile_data = response.entity.model_dump(by_alias=True)
        risk_profile_data["id"] = response.metadata.id
        risk_profile_data["state"] = response.metadata.state

        return risk_profile_data, 200

    except Exception as e:
        logger.error(f"Failed to get risk profile: {str(e)}")
        return {"error": str(e)}, 404


@risk_profiles_bp.route("/<risk_profile_id>", methods=["PUT"])
@validate_request(RiskProfile)
async def update_risk_profile(risk_profile_id: str, data: RiskProfile) -> tuple[Dict[str, Any], int]:
    """
    Update a risk profile.

    Args:
        risk_profile_id: Technical ID of the risk profile
        data: Updated risk profile data

    Returns:
        Updated risk profile
    """
    try:
        entity_service = get_entity_service()

        risk_profile_data = data.model_dump(by_alias=True)
        response = await entity_service.save(
            entity=risk_profile_data,
            entity_class=RiskProfile.ENTITY_NAME,
            entity_version=str(RiskProfile.ENTITY_VERSION),
        )

        risk_profile_data["id"] = response.metadata.id
        risk_profile_data["state"] = response.metadata.state

        logger.info(f"Risk profile updated: {risk_profile_id}")
        return risk_profile_data, 200

    except Exception as e:
        logger.error(f"Failed to update risk profile: {str(e)}")
        return {"error": str(e)}, 400


@risk_profiles_bp.route("/<risk_profile_id>", methods=["DELETE"])
async def delete_risk_profile(risk_profile_id: str) -> tuple[Dict[str, str], int]:
    """
    Delete a risk profile.

    Args:
        risk_profile_id: Technical ID of the risk profile

    Returns:
        Deletion confirmation
    """
    try:
        entity_service = get_entity_service()

        await entity_service.delete(
            entity_id=risk_profile_id,
            entity_class=RiskProfile.ENTITY_NAME,
            entity_version=str(RiskProfile.ENTITY_VERSION),
        )

        logger.info(f"Risk profile deleted: {risk_profile_id}")
        return {"message": "Risk profile deleted successfully"}, 200

    except Exception as e:
        logger.error(f"Failed to delete risk profile: {str(e)}")
        return {"error": str(e)}, 400

