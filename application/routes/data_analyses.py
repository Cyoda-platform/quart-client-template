"""
DataAnalysis Routes for CSV analysis and reporting.

Manages all DataAnalysis-related API endpoints.
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from quart import Blueprint, jsonify
from quart.typing import ResponseReturnValue
from quart_schema import operation_id, tag, validate

from application.entity.data_analysis import DataAnalysis
from services.services import get_entity_service

logger = logging.getLogger(__name__)


class _ServiceProxy:
    def __getattr__(self, name: str) -> Any:
        return getattr(get_entity_service(), name)


service = _ServiceProxy()


def _to_entity_dict(data: Any) -> Dict[str, Any]:
    return data.model_dump(by_alias=True) if hasattr(data, "model_dump") else data


data_analyses_bp = Blueprint(
    "data_analyses", __name__, url_prefix="/api/data-analyses"
)


@data_analyses_bp.route("", methods=["POST"])
@tag(["data-analyses"])
@operation_id("create_data_analysis")
@validate(
    request=DataAnalysis,
    responses={
        201: (Dict[str, Any], None),
        400: (Dict[str, str], None),
        500: (Dict[str, str], None),
    },
)
async def create_data_analysis(data: DataAnalysis) -> ResponseReturnValue:
    """Create a new DataAnalysis job"""
    try:
        entity_data = data.model_dump(by_alias=True)
        response = await service.save(
            entity=entity_data,
            entity_class=DataAnalysis.ENTITY_NAME,
            entity_version=str(DataAnalysis.ENTITY_VERSION),
        )
        logger.info("Created DataAnalysis with ID: %s", response.metadata.id)
        return _to_entity_dict(response.data), 201

    except ValueError as e:
        logger.warning("Validation error: %s", str(e))
        return {"error": str(e), "code": "VALIDATION_ERROR"}, 400
    except Exception as e:
        logger.exception("Error creating DataAnalysis: %s", str(e))
        return {"error": str(e), "code": "INTERNAL_ERROR"}, 500


@data_analyses_bp.route("/<entity_id>", methods=["GET"])
@tag(["data-analyses"])
@operation_id("get_data_analysis")
@validate(
    responses={
        200: (Dict[str, Any], None),
        404: (Dict[str, str], None),
        500: (Dict[str, str], None),
    }
)
async def get_data_analysis(entity_id: str) -> ResponseReturnValue:
    """Get DataAnalysis by ID"""
    try:
        response = await service.get_by_id(
            entity_id=entity_id,
            entity_class=DataAnalysis.ENTITY_NAME,
            entity_version=str(DataAnalysis.ENTITY_VERSION),
        )
        if not response:
            return {"error": "DataAnalysis not found", "code": "NOT_FOUND"}, 404
        return _to_entity_dict(response.data), 200

    except Exception as e:
        logger.exception("Error getting DataAnalysis: %s", str(e))
        return {"error": str(e), "code": "INTERNAL_ERROR"}, 500


@data_analyses_bp.route("", methods=["GET"])
@tag(["data-analyses"])
@operation_id("list_data_analyses")
@validate(
    responses={
        200: (Dict[str, Any], None),
        500: (Dict[str, str], None),
    }
)
async def list_data_analyses() -> ResponseReturnValue:
    """List all DataAnalysis jobs"""
    try:
        entities = await service.find_all(
            entity_class=DataAnalysis.ENTITY_NAME,
            entity_version=str(DataAnalysis.ENTITY_VERSION),
        )
        entity_list = [_to_entity_dict(r.data) for r in entities]
        return jsonify({"entities": entity_list, "total": len(entity_list)}), 200

    except Exception as e:
        logger.exception("Error listing DataAnalysis: %s", str(e))
        return jsonify({"error": str(e)}), 500


@data_analyses_bp.route("/<entity_id>", methods=["DELETE"])
@tag(["data-analyses"])
@operation_id("delete_data_analysis")
@validate(
    responses={
        200: (Dict[str, Any], None),
        404: (Dict[str, str], None),
        500: (Dict[str, str], None),
    }
)
async def delete_data_analysis(entity_id: str) -> ResponseReturnValue:
    """Delete DataAnalysis by ID"""
    try:
        await service.delete_by_id(
            entity_id=entity_id,
            entity_class=DataAnalysis.ENTITY_NAME,
            entity_version=str(DataAnalysis.ENTITY_VERSION),
        )
        logger.info("Deleted DataAnalysis %s", entity_id)
        return {"success": True, "message": "DataAnalysis deleted"}, 200

    except Exception as e:
        logger.exception("Error deleting DataAnalysis: %s", str(e))
        return {"error": str(e), "code": "INTERNAL_ERROR"}, 500

