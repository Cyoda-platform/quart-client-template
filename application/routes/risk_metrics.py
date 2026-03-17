"""
Risk metrics management routes for institutional trading platform.

Provides REST API endpoints for real-time risk evaluation and monitoring.
"""

import logging
from typing import Any

from quart import Blueprint
from quart_schema import validate_request, validate_response

from application.entity.risk_metrics.version_1.risk_metrics import RiskMetrics
from services.services import get_entity_service

logger = logging.getLogger(__name__)

risk_metrics_bp = Blueprint("risk_metrics", __name__, url_prefix="/api/risk-metrics")


class _ServiceProxy:
    """Lazy proxy to avoid initializing services at import time."""

    def __getattr__(self, name: str) -> Any:
        return getattr(get_entity_service(), name)


service = _ServiceProxy()


@risk_metrics_bp.post("")
@validate_request(RiskMetrics)
@validate_response(RiskMetrics, 201)
async def create_risk_metrics(data: RiskMetrics) -> tuple[dict[str, Any], int]:
    """Create new risk metrics."""
    try:
        entity_data = data.model_dump(by_alias=True)
        response = await service.save(
            entity=entity_data,
            entity_class=RiskMetrics.ENTITY_NAME,
            entity_version=str(RiskMetrics.ENTITY_VERSION),
        )
        logger.info(f"Created risk metrics: {response.metadata.id}")
        return response.data, 201
    except Exception as e:
        logger.error(f"Error creating risk metrics: {str(e)}")
        return {"error": str(e)}, 400


@risk_metrics_bp.get("/<risk_id>")
@validate_response(RiskMetrics, 200)
async def get_risk_metrics(risk_id: str) -> tuple[dict[str, Any], int]:
    """Get risk metrics by ID."""
    try:
        response = await service.get(
            entity_id=risk_id,
            entity_class=RiskMetrics.ENTITY_NAME,
        )
        return response.data, 200
    except Exception as e:
        logger.error(f"Error getting risk metrics: {str(e)}")
        return {"error": str(e)}, 404


@risk_metrics_bp.put("/<risk_id>")
@validate_request(RiskMetrics)
@validate_response(RiskMetrics, 200)
async def update_risk_metrics(
    risk_id: str, data: RiskMetrics
) -> tuple[dict[str, Any], int]:
    """Update risk metrics."""
    try:
        entity_data = data.model_dump(by_alias=True)
        response = await service.update(
            entity_id=risk_id,
            entity=entity_data,
            entity_class=RiskMetrics.ENTITY_NAME,
        )
        logger.info(f"Updated risk metrics: {risk_id}")
        return response.data, 200
    except Exception as e:
        logger.error(f"Error updating risk metrics: {str(e)}")
        return {"error": str(e)}, 400


@risk_metrics_bp.post("/<risk_id>/transitions/<transition_name>")
async def transition_risk_metrics(
    risk_id: str, transition_name: str
) -> tuple[dict[str, Any], int]:
    """Trigger a workflow transition on risk metrics."""
    try:
        response = await service.transition(
            entity_id=risk_id,
            transition_name=transition_name,
            entity_class=RiskMetrics.ENTITY_NAME,
        )
        logger.info(f"Transitioned risk metrics {risk_id} to {transition_name}")
        return response.data, 200
    except Exception as e:
        logger.error(f"Error transitioning risk metrics: {str(e)}")
        return {"error": str(e)}, 400
