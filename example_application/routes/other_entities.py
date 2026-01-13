"""
OtherEntity Routes for Cyoda Client Application

Manages all OtherEntity-related API endpoints including CRUD operations
and workflow transitions as specified in functional requirements.
"""

import logging
from datetime import datetime
from typing import Any, Dict, Optional, Tuple

from pydantic import BaseModel, Field
from quart import Blueprint, request
from quart_schema import (
    operation_id,
    tag,
    validate,
    validate_querystring,
)

from common.exception import is_not_found
from common.service.entity_service import (
    SearchConditionRequest,
)
from services.services import get_entity_service

# Imported for entity constants
from ..entity.other_entity import OtherEntity  # noqa: F401
from ..models.request_models import (
    OtherEntitySearchRequest,
    OtherEntityUpdateQueryParams,
    TransitionRequest,
)
from ..models.response_models import (
    CountResponse,
    DeleteResponse,
    ErrorResponse,
    ExistsResponse,
    OtherEntityListResponse,
    OtherEntityResponse,
    TransitionResponse,
    TransitionsResponse,
    ValidationErrorResponse,
)

logger = logging.getLogger(__name__)

other_entities_bp = Blueprint(
    "other_entities", __name__, url_prefix="/api/other-entities"
)
# Module-level service instance to avoid repeated lookups
# Lazy proxy to avoid initializing services at import time


class _ServiceProxy:
    def __getattr__(self, name: str) -> Any:
        return getattr(get_entity_service(), name)


service = _ServiceProxy()


# Helper to normalize entity data from service (Pydantic model or dict)
def _to_entity_dict(data: Any) -> Dict[str, Any]:
    if data is None:
        raise ValueError("Cannot serialize None entity to dictionary")
    return data.model_dump(by_alias=True) if hasattr(data, "model_dump") else data


# Removed unnecessary wrapper - use get_entity_service() directly


class OtherEntityQueryParams(BaseModel):
    """Query parameters for OtherEntity listing"""

    source_entity_id: Optional[str] = Field(
        default=None, alias="sourceEntityId", description="Filter by source entity ID"
    )
    priority: Optional[str] = Field(
        default=None, description="Filter by priority level"
    )
    state: Optional[str] = Field(default=None, description="Filter by workflow state")
    limit: int = Field(default=50, description="Number of results")
    offset: int = Field(default=0, description="Pagination offset")


@other_entities_bp.route("", methods=["POST"])
@tag(["other-entities"])
@operation_id("create_other_entity")
@validate(
    request=OtherEntity,
    responses={
        201: (OtherEntityResponse, None),
        400: (ValidationErrorResponse, None),
        500: (ErrorResponse, None),
    },
)
async def create_other_entity(data: OtherEntity) -> Tuple[Dict[str, Any], int]:
    """Create a new OtherEntity with comprehensive validation"""
    try:
        # Convert request to entity data (entity model as-is)
        entity_data = data.model_dump(by_alias=True)

        # Save the entity
        response = await service.save(
            entity=entity_data,
            entity_class=OtherEntity.ENTITY_NAME,
            entity_version=str(OtherEntity.ENTITY_VERSION),
        )

        logger.info("Created OtherEntity with ID: %s", response.metadata.id)

        # Return created entity directly (thin proxy)
        return _to_entity_dict(response.data), 201

    except ValueError as e:
        logger.warning("Validation error creating OtherEntity: %s", str(e))
        return {"error": str(e), "code": "VALIDATION_ERROR"}, 400
    except Exception as e:  # pragma: no cover - keep robust error handling
        logger.exception("Error creating OtherEntity: %s", str(e))
        return {"error": str(e), "code": "INTERNAL_ERROR"}, 500


@other_entities_bp.route("/<entity_id>", methods=["GET"])
@tag(["other-entities"])
@operation_id("get_other_entity")
@validate(
    responses={
        200: (OtherEntityResponse, None),
        404: (ErrorResponse, None),
        400: (ErrorResponse, None),
        500: (ErrorResponse, None),
    }
)
async def get_other_entity(entity_id: str) -> Tuple[Dict[str, Any], int]:
    """Get OtherEntity by ID with validation"""
    try:
        response = await service.get_by_id(
            entity_id=entity_id,
            entity_class=OtherEntity.ENTITY_NAME,
            entity_version=str(OtherEntity.ENTITY_VERSION),
        )

        if not response:
            return {"error": "OtherEntity not found", "code": "NOT_FOUND"}, 404

        # Thin proxy: return the entity directly
        return _to_entity_dict(response.data), 200

    except ValueError as e:
        logger.warning("Invalid entity ID %s: %s", entity_id, str(e))
        return {"error": str(e), "code": "INVALID_ID"}, 400
    except Exception as e:  # pragma: no cover
        logger.exception("Error getting OtherEntity %s: %s", entity_id, str(e))
        return {"error": str(e), "code": "INTERNAL_ERROR"}, 500


@other_entities_bp.route("", methods=["GET"])
@validate_querystring(OtherEntityQueryParams)
@tag(["other-entities"])
@operation_id("list_other_entities")
@validate(
    responses={
        200: (OtherEntityListResponse, None),
        400: (ValidationErrorResponse, None),
        500: (ErrorResponse, None),
    }
)
async def list_other_entities(
    query_args: OtherEntityQueryParams,
) -> Tuple[Dict[str, Any], int]:
    """List OtherEntities with optional filtering and validation"""
    try:
        # Build search conditions based on query parameters
        search_conditions = {}

        if query_args.source_entity_id:
            search_conditions["sourceEntityId"] = query_args.source_entity_id

        if query_args.priority:
            search_conditions["priority"] = query_args.priority

        if query_args.state:
            search_conditions["state"] = query_args.state

        # Get entities
        if search_conditions:
            # Build SearchConditionRequest from the search conditions
            condition_builder = SearchConditionRequest.builder()
            for field, value in search_conditions.items():
                condition_builder.equals(field, value)
            condition = condition_builder.build()

            entities = await service.search(
                entity_class=OtherEntity.ENTITY_NAME,
                condition=condition,
                entity_version=str(OtherEntity.ENTITY_VERSION),
            )
        else:
            entities = await service.find_all(
                entity_class=OtherEntity.ENTITY_NAME,
                entity_version=str(OtherEntity.ENTITY_VERSION),
            )

        # Thin proxy: return entities directly
        entity_list = [_to_entity_dict(r.data) for r in entities]

        # Apply pagination
        start = query_args.offset
        end = start + query_args.limit
        paginated_entities = entity_list[start:end]

        return {"entities": paginated_entities, "total": len(entity_list)}, 200

    except Exception as e:
        logger.exception("Error listing OtherEntities: %s", str(e))
        return {"error": str(e)}, 500


@other_entities_bp.route("/<entity_id>", methods=["PUT"])
@validate_querystring(OtherEntityUpdateQueryParams)
@tag(["other-entities"])
@operation_id("update_other_entity")
@validate(
    request=OtherEntity,
    responses={
        200: (OtherEntityResponse, None),
        404: (ErrorResponse, None),
        400: (ValidationErrorResponse, None),
        500: (ErrorResponse, None),
    },
)
async def update_other_entity(
    entity_id: str, data: OtherEntity, query_args: OtherEntityUpdateQueryParams
) -> Tuple[Dict[str, Any], int]:
    """Update OtherEntity and optionally trigger workflow transition with validation"""
    try:
        # Convert request to entity data (entity model as-is)
        entity_data = data.model_dump(by_alias=True)

        # Update the entity
        response = await service.update(
            entity_id=entity_id,
            entity=entity_data,
            entity_class=OtherEntity.ENTITY_NAME,
            transition=query_args.transition,
            entity_version=str(OtherEntity.ENTITY_VERSION),
        )

        logger.info("Updated OtherEntity %s", entity_id)

        # Return updated entity directly (thin proxy)
        return _to_entity_dict(response.data), 200

    except ValueError as e:
        logger.warning(
            "Validation error updating OtherEntity %s: %s", entity_id, str(e)
        )
        return {"error": str(e), "code": "VALIDATION_ERROR"}, 400
    except Exception as e:  # pragma: no cover
        logger.exception("Error updating OtherEntity %s: %s", entity_id, str(e))
        return {"error": str(e), "code": "INTERNAL_ERROR"}, 500


@other_entities_bp.route("/<entity_id>", methods=["DELETE"])
@tag(["other-entities"])
@operation_id("delete_other_entity")
@validate(
    responses={
        200: (DeleteResponse, None),
        404: (ErrorResponse, None),
        400: (ErrorResponse, None),
        500: (ErrorResponse, None),
    }
)
async def delete_other_entity(entity_id: str) -> Tuple[Dict[str, Any], int]:
    """Delete OtherEntity with validation"""
    try:
        await service.delete_by_id(
            entity_id=entity_id,
            entity_class=OtherEntity.ENTITY_NAME,
            entity_version=str(OtherEntity.ENTITY_VERSION),
        )

        logger.info("Deleted OtherEntity %s", entity_id)

        # Thin proxy: return success message
        response = DeleteResponse(
            success=True,
            message="OtherEntity deleted successfully",
            entity_id=entity_id,
        )
        return response.model_dump(), 200

    except ValueError as e:
        logger.warning("Invalid entity ID %s: %s", entity_id, str(e))
        return {"error": str(e), "code": "INVALID_ID"}, 400
    except Exception as e:  # pragma: no cover
        logger.exception("Error deleting OtherEntity %s: %s", entity_id, str(e))
        return {"error": str(e), "code": "INTERNAL_ERROR"}, 500


# ---- Additional Entity Service Endpoints ----------------------------------------


@other_entities_bp.route("/by-business-id/<business_id>", methods=["GET"])
@tag(["other-entities"])
@operation_id("get_other_entity_by_business_id")
@validate(
    responses={
        200: (OtherEntityResponse, None),
        404: (ErrorResponse, None),
        500: (ErrorResponse, None),
    }
)
async def get_by_business_id(business_id: str) -> Tuple[Dict[str, Any], int]:
    """Get OtherEntity by business ID (title field by default)"""
    try:
        business_id_field = request.args.get("field", "title")  # Default to title field

        result = await service.find_by_business_id(
            entity_class=OtherEntity.ENTITY_NAME,
            business_id=business_id,
            business_id_field=business_id_field,
            entity_version=str(OtherEntity.ENTITY_VERSION),
        )

        if not result:
            return {"error": "OtherEntity not found", "code": "NOT_FOUND"}, 404

        # Thin proxy: return the entity directly
        return _to_entity_dict(result.data), 200

    except Exception as e:
        logger.exception(
            "Error getting OtherEntity by business ID %s: %s", business_id, str(e)
        )
        return {"error": str(e)}, 500


@other_entities_bp.route("/<entity_id>/exists", methods=["GET"])
@tag(["other-entities"])
@operation_id("check_other_entity_exists")
@validate(responses={200: (ExistsResponse, None), 500: (ErrorResponse, None)})
async def check_exists(entity_id: str) -> Tuple[Dict[str, Any], int]:
    """Check if OtherEntity exists by ID"""
    try:
        exists = await service.exists_by_id(
            entity_id=entity_id,
            entity_class=OtherEntity.ENTITY_NAME,
            entity_version=str(OtherEntity.ENTITY_VERSION),
        )

        response = ExistsResponse(exists=exists, entity_id=entity_id)
        return response.model_dump(), 200

    except Exception as e:
        logger.exception(
            "Error checking OtherEntity existence %s: %s", entity_id, str(e)
        )
        return {"error": str(e)}, 500


@other_entities_bp.route("/count", methods=["GET"])
@tag(["other-entities"])
@operation_id("count_other_entities")
@validate(responses={200: (CountResponse, None), 500: (ErrorResponse, None)})
async def count_entities() -> Tuple[Dict[str, Any], int]:
    """Count total number of OtherEntities"""
    try:
        count = await service.count(
            entity_class=OtherEntity.ENTITY_NAME,
            entity_version=str(OtherEntity.ENTITY_VERSION),
        )

        response = CountResponse(count=count)
        return response.model_dump(), 200

    except Exception as e:
        logger.exception("Error counting OtherEntities: %s", str(e))
        return {"error": str(e)}, 500


@other_entities_bp.route("/<entity_id>/transitions", methods=["GET"])
@tag(["other-entities"])
@operation_id("get_other_entity_transitions")
@validate(
    responses={
        200: (TransitionsResponse, None),
        404: (ErrorResponse, None),
        500: (ErrorResponse, None),
    }
)
async def get_available_transitions(entity_id: str) -> Tuple[Dict[str, Any], int]:
    """Get available workflow transitions for OtherEntity"""
    try:
        transitions = await service.get_transitions(
            entity_id=entity_id,
            entity_class=OtherEntity.ENTITY_NAME,
            entity_version=str(OtherEntity.ENTITY_VERSION),
        )

        # Get current entity to determine state
        entity_response = await service.get_by_id(
            entity_id=entity_id,
            entity_class=OtherEntity.ENTITY_NAME,
            entity_version=str(OtherEntity.ENTITY_VERSION),
        )
        current_state = entity_response.data.state if entity_response else None

        response = TransitionsResponse(
            entity_id=entity_id,
            available_transitions=transitions,
            current_state=current_state,
        )
        return response.model_dump(), 200

    except Exception as e:
        logger.exception(
            "Error getting transitions for OtherEntity %s: %s", entity_id, str(e)
        )
        return {"error": str(e)}, 500


@other_entities_bp.route("/<entity_id>/transitions", methods=["POST"])
@tag(["other-entities"])
@operation_id("trigger_other_entity_transition")
@validate(
    request=TransitionRequest,
    responses={
        200: (TransitionResponse, None),
        404: (ErrorResponse, None),
        400: (ValidationErrorResponse, None),
        500: (ErrorResponse, None),
    },
)
async def trigger_transition(
    entity_id: str, data: TransitionRequest
) -> Tuple[Dict[str, Any], int]:
    """Trigger workflow transition for OtherEntity with validation"""
    try:
        # Trigger the transition
        response = await service.trigger_transition(
            entity_id=entity_id,
            transition_name=data.transition_name,
            entity_class=OtherEntity.ENTITY_NAME,
            entity_version=str(OtherEntity.ENTITY_VERSION),
        )

        logger.info(
            "Triggered transition %s for OtherEntity %s",
            data.transition_name,
            entity_id,
        )

        # Return transition result directly (thin proxy)
        return _to_entity_dict(response.data), 200

    except ValueError as e:
        logger.warning(
            "Validation error triggering transition for OtherEntity %s: %s",
            entity_id,
            str(e),
        )
        return {"error": str(e), "code": "VALIDATION_ERROR"}, 400
    except Exception as e:  # pragma: no cover
        logger.exception(
            "Error triggering transition for OtherEntity %s: %s", entity_id, str(e)
        )
        return {"error": str(e), "code": "INTERNAL_ERROR"}, 500


# ---- Search Endpoints -----------------------------------------------------------


@other_entities_bp.route("/search", methods=["POST"])
@tag(["other-entities"])
@operation_id("search_other_entities")
@validate(
    request=OtherEntitySearchRequest,
    responses={
        200: (OtherEntityListResponse, None),
        400: (ValidationErrorResponse, None),
        500: (ErrorResponse, None),
    },
)
async def search_entities(data: OtherEntitySearchRequest) -> Tuple[Dict[str, Any], int]:
    """Search OtherEntities using simple field-value search with validation"""
    try:
        # Convert Pydantic model to dict for search
        search_data = data.model_dump(by_alias=True, exclude_none=True)

        if not search_data:
            return {"error": "Search conditions required", "code": "EMPTY_SEARCH"}, 400

        # KISS: Simple field-value search only
        builder = SearchConditionRequest.builder()
        for field, value in search_data.items():
            builder.equals(field, value)

        search_request = builder.build()
        results = await service.search(
            entity_class=OtherEntity.ENTITY_NAME,
            condition=search_request,
            entity_version=str(OtherEntity.ENTITY_VERSION),
        )

        # Thin proxy: return list of entities directly
        entities = [_to_entity_dict(r.data) for r in results]
        return {"entities": entities, "total": len(entities)}, 200

    except Exception as e:
        logger.exception("Error searching OtherEntities: %s", str(e))
        return {"error": str(e)}, 500


@other_entities_bp.route("/find-all", methods=["GET"])
@tag(["other-entities"])
@operation_id("find_all_other_entities")
@validate(responses={200: (OtherEntityListResponse, None), 500: (ErrorResponse, None)})
async def find_all_entities() -> Tuple[Dict[str, Any], int]:
    """Find all OtherEntities"""
    try:
        results = await service.find_all(
            entity_class=OtherEntity.ENTITY_NAME,
            entity_version=str(OtherEntity.ENTITY_VERSION),
        )

        entities = [_to_entity_dict(r.data) for r in results]
        return {"entities": entities, "total": len(entities)}, 200

    except Exception as e:
        logger.exception("Error finding all OtherEntities: %s", str(e))
        return {"error": str(e)}, 500


# ---- Temporal Query Endpoints (PR #41) ------------------------------------------


@other_entities_bp.route("/<entity_id>/at-time", methods=["GET"])
@tag(["other-entities"])
@operation_id("get_other_entity_at_time")
@validate(
    responses={
        200: (OtherEntityResponse, None),
        404: (ErrorResponse, None),
        400: (ErrorResponse, None),
        500: (ErrorResponse, None),
    }
)
async def get_entity_at_time(entity_id: str) -> Tuple[Dict[str, Any], int]:
    """Get OtherEntity as it existed at a specific point in time"""
    try:
        point_in_time_str = request.args.get("pointInTime")
        if not point_in_time_str:
            return (
                {
                    "error": "pointInTime query parameter required (ISO 8601 format)",
                    "code": "MISSING_PARAMETER",
                },
                400,
            )

        # Parse ISO 8601 datetime
        try:
            point_in_time = datetime.fromisoformat(
                point_in_time_str.replace("Z", "+00:00")
            )
        except ValueError as e:
            return (
                {
                    "error": f"Invalid datetime format: {str(e)}",
                    "code": "INVALID_DATETIME",
                },
                400,
            )

        response = await service.get_by_id_at_time(
            entity_id=entity_id,
            entity_class=OtherEntity.ENTITY_NAME,
            point_in_time=point_in_time,
            entity_version=str(OtherEntity.ENTITY_VERSION),
        )

        if not response:
            return {"error": "OtherEntity not found", "code": "NOT_FOUND"}, 404

        return _to_entity_dict(response.data), 200

    except Exception as e:
        if is_not_found(e):
            return {"error": "OtherEntity not found", "code": "NOT_FOUND"}, 404
        logger.exception(
            "Error getting OtherEntity %s at time %s: %s",
            entity_id,
            point_in_time_str,
            str(e),
        )
        return {"error": str(e), "code": "INTERNAL_ERROR"}, 500


@other_entities_bp.route("/by-business-id/<business_id>/at-time", methods=["GET"])
@tag(["other-entities"])
@operation_id("get_other_entity_by_business_id_at_time")
@validate(
    responses={
        200: (OtherEntityResponse, None),
        404: (ErrorResponse, None),
        400: (ErrorResponse, None),
        500: (ErrorResponse, None),
    }
)
async def get_by_business_id_at_time(business_id: str) -> Tuple[Dict[str, Any], int]:
    """Get OtherEntity by business ID as it existed at a specific point in time"""
    try:
        business_id_field = request.args.get("field", "title")
        point_in_time_str = request.args.get("pointInTime")

        if not point_in_time_str:
            return (
                {
                    "error": "pointInTime query parameter required (ISO 8601 format)",
                    "code": "MISSING_PARAMETER",
                },
                400,
            )

        # Parse datetime
        try:
            point_in_time = datetime.fromisoformat(
                point_in_time_str.replace("Z", "+00:00")
            )
        except ValueError as e:
            return (
                {
                    "error": f"Invalid datetime format: {str(e)}",
                    "code": "INVALID_DATETIME",
                },
                400,
            )

        result = await service.find_by_business_id_at_time(
            entity_class=OtherEntity.ENTITY_NAME,
            business_id=business_id,
            business_id_field=business_id_field,
            point_in_time=point_in_time,
            entity_version=str(OtherEntity.ENTITY_VERSION),
        )

        if not result:
            return {"error": "OtherEntity not found", "code": "NOT_FOUND"}, 404

        return _to_entity_dict(result.data), 200

    except Exception as e:
        if is_not_found(e):
            return {"error": "OtherEntity not found", "code": "NOT_FOUND"}, 404
        logger.exception(
            "Error getting OtherEntity by business ID %s at time: %s",
            business_id,
            str(e),
        )
        return {"error": str(e)}, 500


@other_entities_bp.route("/at-time", methods=["GET"])
@tag(["other-entities"])
@operation_id("list_other_entities_at_time")
@validate(
    responses={
        200: (OtherEntityListResponse, None),
        400: (ErrorResponse, None),
        500: (ErrorResponse, None),
    }
)
async def list_entities_at_time() -> Tuple[Dict[str, Any], int]:
    """List all OtherEntities as they existed at a specific point in time"""
    try:
        point_in_time_str = request.args.get("pointInTime")
        if not point_in_time_str:
            return (
                {
                    "error": "pointInTime query parameter required (ISO 8601 format)",
                    "code": "MISSING_PARAMETER",
                },
                400,
            )

        # Parse datetime
        try:
            point_in_time = datetime.fromisoformat(
                point_in_time_str.replace("Z", "+00:00")
            )
        except ValueError as e:
            return (
                {
                    "error": f"Invalid datetime format: {str(e)}",
                    "code": "INVALID_DATETIME",
                },
                400,
            )

        results = await service.find_all_at_time(
            entity_class=OtherEntity.ENTITY_NAME,
            point_in_time=point_in_time,
            entity_version=str(OtherEntity.ENTITY_VERSION),
        )

        entities = [_to_entity_dict(r.data) for r in results]
        return {"entities": entities, "total": len(entities)}, 200

    except Exception as e:
        logger.exception("Error listing OtherEntities at time: %s", str(e))
        return {"error": str(e)}, 500


@other_entities_bp.route("/search/at-time", methods=["POST"])
@tag(["other-entities"])
@operation_id("search_other_entities_at_time")
@validate(
    request=OtherEntitySearchRequest,
    responses={
        200: (OtherEntityListResponse, None),
        400: (ValidationErrorResponse, None),
        500: (ErrorResponse, None),
    },
)
async def search_entities_at_time(
    data: OtherEntitySearchRequest,
) -> Tuple[Dict[str, Any], int]:
    """Search OtherEntities as they existed at a specific point in time"""
    try:
        point_in_time_str = request.args.get("pointInTime")
        if not point_in_time_str:
            return (
                {
                    "error": "pointInTime query parameter required (ISO 8601 format)",
                    "code": "MISSING_PARAMETER",
                },
                400,
            )

        # Parse datetime
        try:
            point_in_time = datetime.fromisoformat(
                point_in_time_str.replace("Z", "+00:00")
            )
        except ValueError as e:
            return (
                {
                    "error": f"Invalid datetime format: {str(e)}",
                    "code": "INVALID_DATETIME",
                },
                400,
            )

        # Build search conditions
        search_data = data.model_dump(by_alias=True, exclude_none=True)
        if not search_data:
            return {"error": "Search conditions required", "code": "EMPTY_SEARCH"}, 400

        builder = SearchConditionRequest.builder()
        for field, value in search_data.items():
            builder.equals(field, value)

        search_request = builder.build()
        results = await service.search_at_time(
            entity_class=OtherEntity.ENTITY_NAME,
            condition=search_request,
            point_in_time=point_in_time,
            entity_version=str(OtherEntity.ENTITY_VERSION),
        )

        entities = [_to_entity_dict(r.data) for r in results]
        return {"entities": entities, "total": len(entities)}, 200

    except Exception as e:
        logger.exception("Error searching OtherEntities at time: %s", str(e))
        return {"error": str(e)}, 500


@other_entities_bp.route("/count/at-time", methods=["GET"])
@tag(["other-entities"])
@operation_id("count_other_entities_at_time")
@validate(
    responses={
        200: (CountResponse, None),
        400: (ErrorResponse, None),
        500: (ErrorResponse, None),
    }
)
async def count_entities_at_time() -> Tuple[Dict[str, Any], int]:
    """Count OtherEntities as they existed at a specific point in time"""
    try:
        point_in_time_str = request.args.get("pointInTime")
        if not point_in_time_str:
            return (
                {
                    "error": "pointInTime query parameter required (ISO 8601 format)",
                    "code": "MISSING_PARAMETER",
                },
                400,
            )

        # Parse datetime
        try:
            point_in_time = datetime.fromisoformat(
                point_in_time_str.replace("Z", "+00:00")
            )
        except ValueError as e:
            return (
                {
                    "error": f"Invalid datetime format: {str(e)}",
                    "code": "INVALID_DATETIME",
                },
                400,
            )

        count = await service.get_entity_count(
            entity_class=OtherEntity.ENTITY_NAME,
            entity_version=str(OtherEntity.ENTITY_VERSION),
            point_in_time=point_in_time,
        )

        response = CountResponse(count=count)
        return response.model_dump(), 200

    except Exception as e:
        logger.exception("Error counting OtherEntities at time: %s", str(e))
        return {"error": str(e)}, 500


@other_entities_bp.route("/<entity_id>/changes", methods=["GET"])
@tag(["other-entities"])
@operation_id("get_other_entity_changes")
@validate(
    responses={
        200: (Dict[str, Any], None),
        404: (ErrorResponse, None),
        500: (ErrorResponse, None),
    }
)
async def get_entity_changes(entity_id: str) -> Tuple[Dict[str, Any], int]:
    """Get change history metadata for OtherEntity"""
    try:
        # Optional point_in_time parameter
        point_in_time = None
        point_in_time_str = request.args.get("pointInTime")
        if point_in_time_str:
            try:
                point_in_time = datetime.fromisoformat(
                    point_in_time_str.replace("Z", "+00:00")
                )
            except ValueError as e:
                return (
                    {
                        "error": f"Invalid datetime format: {str(e)}",
                        "code": "INVALID_DATETIME",
                    },
                    400,
                )

        changes = await service.get_entity_changes_metadata(
            entity_id=entity_id,
            entity_class=OtherEntity.ENTITY_NAME,
            entity_version=str(OtherEntity.ENTITY_VERSION),
            point_in_time=point_in_time,
        )

        return {"entity_id": entity_id, "changes": changes}, 200

    except Exception as e:
        if is_not_found(e):
            return {"error": "OtherEntity not found", "code": "NOT_FOUND"}, 404
        logger.exception(
            "Error getting changes for OtherEntity %s: %s", entity_id, str(e)
        )
        return {"error": str(e)}, 500
