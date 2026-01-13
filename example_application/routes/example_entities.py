"""
ExampleEntity Routes for Cyoda Client Application

Manages all ExampleEntity-related API endpoints including CRUD operations
and workflow transitions as specified in functional requirements.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, Optional

from quart import Blueprint, jsonify, request
from quart.typing import ResponseReturnValue
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

# Imported for entity constants / typing
from ..entity.example_entity import ExampleEntity  # noqa: F401
from ..entity.other_entity import OtherEntity  # noqa: F401
from ..models import (
    CountResponse,
    DeleteResponse,
    ErrorResponse,
    ExampleEntityListResponse,
    ExampleEntityQueryParams,
    ExampleEntityResponse,
    ExampleEntitySearchResponse,
    ExampleEntityUpdateQueryParams,
    ExistsResponse,
    SearchRequest,
    TransitionRequest,
    TransitionResponse,
    TransitionsResponse,
    ValidationErrorResponse,
)

# Module-level service instance to avoid repeated lookups
# Lazy proxy to avoid initializing services at import time


class _ServiceProxy:
    def __getattr__(self, name: str) -> Any:
        return getattr(get_entity_service(), name)


service = _ServiceProxy()


logger = logging.getLogger(__name__)


# Helper to normalize entity data from service (Pydantic model or dict)
def _to_entity_dict(data: Any) -> Dict[str, Any]:
    if data is None:
        raise ValueError("Cannot serialize None entity to dictionary")
    return data.model_dump(by_alias=True) if hasattr(data, "model_dump") else data


example_entities_bp = Blueprint(
    "example_entities", __name__, url_prefix="/api/example-entities"
)


# Remove duplicate models - using ones from models package


# ---- Routes -----------------------------------------------------------------


@example_entities_bp.route("", methods=["POST"])
@tag(["example-entities"])
@operation_id("create_example_entity")
@validate(
    request=ExampleEntity,
    responses={
        201: (ExampleEntityResponse, None),
        400: (ValidationErrorResponse, None),
        500: (ErrorResponse, None),
    },
)
async def create_example_entity(
    data: ExampleEntity,
) -> ResponseReturnValue:
    """Create a new ExampleEntity with comprehensive validation"""
    try:
        # Convert request to entity data (same pattern as OtherEntity)
        entity_data = data.model_dump(by_alias=True)

        # Save the entity
        response = await service.save(
            entity=entity_data,
            entity_class=ExampleEntity.ENTITY_NAME,
            entity_version=str(ExampleEntity.ENTITY_VERSION),
        )

        logger.info("Created ExampleEntity with ID: %s", response.metadata.id)

        # Return created entity directly (thin proxy)
        return _to_entity_dict(response.data), 201

    except ValueError as e:
        logger.warning("Validation error creating ExampleEntity: %s", str(e))
        return {"error": str(e), "code": "VALIDATION_ERROR"}, 400
    except Exception as e:  # pragma: no cover - keep robust error handling
        logger.exception("Error creating ExampleEntity: %s", str(e))
        return {"error": str(e), "code": "INTERNAL_ERROR"}, 500


@example_entities_bp.route("/<entity_id>", methods=["GET"])
@tag(["example-entities"])
@operation_id("get_example_entity")
@validate(
    responses={
        200: (ExampleEntityResponse, None),
        404: (ErrorResponse, None),
        400: (ErrorResponse, None),
        500: (ErrorResponse, None),
    }
)
async def get_example_entity(entity_id: str) -> ResponseReturnValue:
    """Get ExampleEntity by ID with validation"""
    try:
        # Validate entity ID format
        if not entity_id or len(entity_id.strip()) == 0:
            return (
                jsonify({"error": "Entity ID is required", "code": "INVALID_ID"}),
                400,
            )

        response = await service.get_by_id(
            entity_id=entity_id,
            entity_class=ExampleEntity.ENTITY_NAME,
            entity_version=str(ExampleEntity.ENTITY_VERSION),
        )

        if not response:
            return {"error": "ExampleEntity not found", "code": "NOT_FOUND"}, 404

        # Thin proxy: return the entity directly
        return _to_entity_dict(response.data), 200

    except ValueError as e:
        logger.warning("Invalid entity ID %s: %s", entity_id, str(e))
        return {"error": str(e), "code": "INVALID_ID"}, 400
    except Exception as e:  # pragma: no cover
        logger.exception("Error getting ExampleEntity %s: %s", entity_id, str(e))
        return {"error": str(e), "code": "INTERNAL_ERROR"}, 500


@example_entities_bp.route("", methods=["GET"])
@validate_querystring(ExampleEntityQueryParams)
@tag(["example-entities"])
@operation_id("list_example_entities")
@validate(
    responses={
        200: (ExampleEntityListResponse, None),
        400: (ValidationErrorResponse, None),
        500: (ErrorResponse, None),
    }
)
async def list_example_entities(
    query_args: ExampleEntityQueryParams,
) -> ResponseReturnValue:
    """List ExampleEntities with optional filtering and validation"""
    try:
        # Build search conditions based on query parameters
        search_conditions: Dict[str, str] = {}

        if query_args.category:
            search_conditions["category"] = query_args.category

        if query_args.is_active is not None:
            search_conditions["isActive"] = str(query_args.is_active).lower()

        if query_args.state:
            search_conditions["state"] = query_args.state

        # Get entities
        if search_conditions:
            # Build search condition request
            builder = SearchConditionRequest.builder()
            for field, value in search_conditions.items():
                builder.equals(field, value)
            condition = builder.build()

            entities = await service.search(
                entity_class=ExampleEntity.ENTITY_NAME,
                condition=condition,
                entity_version=str(ExampleEntity.ENTITY_VERSION),
            )
        else:
            entities = await service.find_all(
                entity_class=ExampleEntity.ENTITY_NAME,
                entity_version=str(ExampleEntity.ENTITY_VERSION),
            )

        # Thin proxy: return entities directly
        entity_list = [_to_entity_dict(r.data) for r in entities]

        # Apply pagination
        start = query_args.offset
        end = start + query_args.limit
        paginated_entities = entity_list[start:end]

        return jsonify({"entities": paginated_entities, "total": len(entity_list)}), 200

    except Exception as e:  # pragma: no cover
        logger.exception("Error listing ExampleEntities: %s", str(e))
        return jsonify({"error": str(e)}), 500


@example_entities_bp.route("/<entity_id>", methods=["PUT"])
@validate_querystring(ExampleEntityUpdateQueryParams)
@tag(["example-entities"])
@operation_id("update_example_entity")
@validate(
    request=ExampleEntity,
    responses={
        200: (ExampleEntityResponse, None),
        404: (ErrorResponse, None),
        400: (ValidationErrorResponse, None),
        500: (ErrorResponse, None),
    },
)
async def update_example_entity(
    entity_id: str, data: ExampleEntity, query_args: ExampleEntityUpdateQueryParams
) -> ResponseReturnValue:
    """Update ExampleEntity and optionally trigger workflow transition with validation"""
    try:
        # Validate entity ID format
        if not entity_id or len(entity_id.strip()) == 0:
            return (
                jsonify({"error": "Entity ID is required", "code": "INVALID_ID"}),
                400,
            )

        # Get transition from query parameters
        transition: Optional[str] = query_args.transition

        # Convert request to entity data (entity model as-is)
        entity_data: Dict[str, Any] = data.model_dump(by_alias=True)

        # Update the entity
        response = await service.update(
            entity_id=entity_id,
            entity=entity_data,
            entity_class=ExampleEntity.ENTITY_NAME,
            transition=transition,
            entity_version=str(ExampleEntity.ENTITY_VERSION),
        )

        logger.info("Updated ExampleEntity %s", entity_id)

        # Return updated entity directly (thin proxy)
        return jsonify(_to_entity_dict(response.data)), 200

    except ValueError as e:
        logger.warning(
            "Validation error updating ExampleEntity %s: %s", entity_id, str(e)
        )
        return jsonify({"error": str(e), "code": "VALIDATION_ERROR"}), 400
    except Exception as e:  # pragma: no cover
        logger.exception("Error updating ExampleEntity %s: %s", entity_id, str(e))
        return jsonify({"error": str(e), "code": "INTERNAL_ERROR"}), 500


@example_entities_bp.route("/<entity_id>", methods=["DELETE"])
@tag(["example-entities"])
@operation_id("delete_example_entity")
@validate(
    responses={
        200: (DeleteResponse, None),
        404: (ErrorResponse, None),
        400: (ErrorResponse, None),
        500: (ErrorResponse, None),
    }
)
async def delete_example_entity(entity_id: str) -> ResponseReturnValue:
    """Delete ExampleEntity with validation"""
    try:
        # Validate entity ID format
        if not entity_id or len(entity_id.strip()) == 0:
            return (
                jsonify({"error": "Entity ID is required", "code": "INVALID_ID"}),
                400,
            )

        await service.delete_by_id(
            entity_id=entity_id,
            entity_class=ExampleEntity.ENTITY_NAME,
            entity_version=str(ExampleEntity.ENTITY_VERSION),
        )

        logger.info("Deleted ExampleEntity %s", entity_id)

        # Thin proxy: return success message
        response = DeleteResponse(
            success=True,
            message="ExampleEntity deleted successfully",
            entity_id=entity_id,
        )
        return response.model_dump(), 200

    except ValueError as e:
        logger.warning("Invalid entity ID %s: %s", entity_id, str(e))
        return {"error": str(e), "code": "INVALID_ID"}, 400
    except Exception as e:  # pragma: no cover
        logger.exception("Error deleting ExampleEntity %s: %s", entity_id, str(e))
        return {"error": str(e), "code": "INTERNAL_ERROR"}, 500


# ---- Additional Entity Service Endpoints ----------------------------------------


@example_entities_bp.route("/by-business-id/<business_id>", methods=["GET"])
@tag(["example-entities"])
@operation_id("get_example_entity_by_business_id")
@validate(
    responses={
        200: (ExampleEntityResponse, None),
        404: (ErrorResponse, None),
        500: (ErrorResponse, None),
    }
)
async def get_by_business_id(business_id: str) -> ResponseReturnValue:
    """Get ExampleEntity by business ID (name field by default)"""
    try:
        business_id_field = request.args.get("field", "name")  # Default to name field

        result = await service.find_by_business_id(
            entity_class=ExampleEntity.ENTITY_NAME,
            business_id=business_id,
            business_id_field=business_id_field,
            entity_version=str(ExampleEntity.ENTITY_VERSION),
        )

        if not result:
            return jsonify({"error": "ExampleEntity not found"}), 404

        # Thin proxy: return the entity directly
        return jsonify(_to_entity_dict(result.data)), 200

    except Exception as e:
        logger.exception(
            "Error getting ExampleEntity by business ID %s: %s", business_id, str(e)
        )
        return jsonify({"error": str(e)}), 500


@example_entities_bp.route("/<entity_id>/exists", methods=["GET"])
@tag(["example-entities"])
@operation_id("check_example_entity_exists")
@validate(responses={200: (ExistsResponse, None), 500: (ErrorResponse, None)})
async def check_exists(entity_id: str) -> ResponseReturnValue:
    """Check if ExampleEntity exists by ID"""
    try:
        exists = await service.exists_by_id(
            entity_id=entity_id,
            entity_class=ExampleEntity.ENTITY_NAME,
            entity_version=str(ExampleEntity.ENTITY_VERSION),
        )

        response = ExistsResponse(exists=exists, entity_id=entity_id)
        return response.model_dump(), 200

    except Exception as e:
        logger.exception(
            "Error checking ExampleEntity existence %s: %s", entity_id, str(e)
        )
        return {"error": str(e)}, 500


@example_entities_bp.route("/count", methods=["GET"])
@tag(["example-entities"])
@operation_id("count_example_entities")
@validate(responses={200: (CountResponse, None), 500: (ErrorResponse, None)})
async def count_entities() -> ResponseReturnValue:
    """Count total number of ExampleEntities"""
    try:
        service = get_entity_service()

        count = await service.count(
            entity_class=ExampleEntity.ENTITY_NAME,
            entity_version=str(ExampleEntity.ENTITY_VERSION),
        )

        response = CountResponse(count=count)
        return jsonify(response.model_dump()), 200

    except Exception as e:
        logger.exception("Error counting ExampleEntities: %s", str(e))
        return jsonify({"error": str(e)}), 500


@example_entities_bp.route("/<entity_id>/transitions", methods=["GET"])
@tag(["example-entities"])
@operation_id("get_example_entity_transitions")
@validate(
    responses={
        200: (TransitionsResponse, None),
        404: (ErrorResponse, None),
        500: (ErrorResponse, None),
    }
)
async def get_available_transitions(entity_id: str) -> ResponseReturnValue:
    """Get available workflow transitions for ExampleEntity"""
    try:
        transitions = await service.get_transitions(
            entity_id=entity_id,
            entity_class=ExampleEntity.ENTITY_NAME,
            entity_version=str(ExampleEntity.ENTITY_VERSION),
        )

        response = TransitionsResponse(
            entity_id=entity_id,
            available_transitions=transitions,
            current_state=None,  # Could be enhanced to get current state
        )
        return jsonify(response.model_dump()), 200

    except Exception as e:
        logger.exception(
            "Error getting transitions for ExampleEntity %s: %s", entity_id, str(e)
        )
        return jsonify({"error": str(e)}), 500


# ---- Search Endpoints -----------------------------------------------------------


@example_entities_bp.route("/search", methods=["POST"])
@tag(["example-entities"])
@operation_id("search_example_entities")
@validate(
    request=SearchRequest,
    responses={
        200: (ExampleEntitySearchResponse, None),
        400: (ValidationErrorResponse, None),
        500: (ErrorResponse, None),
    },
)
async def search_entities(data: SearchRequest) -> ResponseReturnValue:
    """Search ExampleEntities using simple field-value search with validation"""
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
            entity_class=ExampleEntity.ENTITY_NAME,
            condition=search_request,
            entity_version=str(ExampleEntity.ENTITY_VERSION),
        )

        # Thin proxy: return list of entities directly
        entities = [_to_entity_dict(r.data) for r in results]

        return {"entities": entities, "total": len(entities)}, 200

    except Exception as e:
        logger.exception("Error searching ExampleEntities: %s", str(e))
        return {"error": str(e)}, 500


@example_entities_bp.route("/find-all", methods=["GET"])
@tag(["example-entities"])
@operation_id("find_all_example_entities")
@validate(
    responses={200: (ExampleEntityListResponse, None), 500: (ErrorResponse, None)}
)
async def find_all_entities() -> ResponseReturnValue:
    """Find all ExampleEntities without filtering"""
    try:
        results = await service.find_all(
            entity_class=ExampleEntity.ENTITY_NAME,
            entity_version=str(ExampleEntity.ENTITY_VERSION),
        )

        entities = [_to_entity_dict(r.data) for r in results]
        return {"entities": entities, "total": len(entities)}, 200

    except Exception as e:
        logger.exception("Error finding all ExampleEntities: %s", str(e))
        return {"error": str(e)}, 500


@example_entities_bp.route("/<entity_id>/transitions", methods=["POST"])
@tag(["example-entities"])
@operation_id("trigger_example_entity_transition")
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
) -> ResponseReturnValue:
    """Trigger a specific workflow transition with validation"""
    try:
        # Get current entity state
        current_entity = await service.get_by_id(
            entity_id=entity_id,
            entity_class=ExampleEntity.ENTITY_NAME,
            entity_version=str(ExampleEntity.ENTITY_VERSION),
        )

        if not current_entity:
            return jsonify({"error": "ExampleEntity not found"}), 404

        previous_state = current_entity.metadata.state

        # Execute the transition
        response = await service.execute_transition(
            entity_id=entity_id,
            transition=data.transition_name,
            entity_class=ExampleEntity.ENTITY_NAME,
            entity_version=str(ExampleEntity.ENTITY_VERSION),
        )

        logger.info(
            "Executed transition '%s' on ExampleEntity %s",
            data.transition_name,
            entity_id,
        )

        return (
            jsonify(
                {
                    "id": response.metadata.id,
                    "message": "Transition executed successfully",
                    "previousState": previous_state,
                    "newState": response.metadata.state,
                }
            ),
            200,
        )

    except Exception as e:  # pragma: no cover
        logger.exception(
            "Error executing transition on ExampleEntity %s: %s", entity_id, str(e)
        )
        return jsonify({"error": str(e)}), 500


# ---- Temporal Query Endpoints (PR #41) ------------------------------------------


@example_entities_bp.route("/<entity_id>/at-time", methods=["GET"])
@tag(["example-entities"])
@operation_id("get_example_entity_at_time")
@validate(
    responses={
        200: (ExampleEntityResponse, None),
        404: (ErrorResponse, None),
        400: (ErrorResponse, None),
        500: (ErrorResponse, None),
    }
)
async def get_entity_at_time(entity_id: str) -> ResponseReturnValue:
    """Get ExampleEntity as it existed at a specific point in time"""
    try:
        # Get pointInTime from query parameters
        point_in_time_str = request.args.get("pointInTime")
        if not point_in_time_str:
            return (
                jsonify(
                    {
                        "error": "pointInTime query parameter required (ISO 8601 format)",
                        "code": "MISSING_PARAMETER",
                    }
                ),
                400,
            )

        # Parse ISO 8601 datetime
        try:
            point_in_time = datetime.fromisoformat(
                point_in_time_str.replace("Z", "+00:00")
            )
        except ValueError as e:
            return (
                jsonify(
                    {
                        "error": f"Invalid datetime format: {str(e)}",
                        "code": "INVALID_DATETIME",
                    }
                ),
                400,
            )

        response = await service.get_by_id_at_time(
            entity_id=entity_id,
            entity_class=ExampleEntity.ENTITY_NAME,
            point_in_time=point_in_time,
            entity_version=str(ExampleEntity.ENTITY_VERSION),
        )

        if not response:
            return {"error": "ExampleEntity not found", "code": "NOT_FOUND"}, 404

        return _to_entity_dict(response.data), 200

    except Exception as e:
        if is_not_found(e):
            return {"error": "ExampleEntity not found", "code": "NOT_FOUND"}, 404
        logger.exception(
            "Error getting ExampleEntity %s at time %s: %s",
            entity_id,
            point_in_time_str,
            str(e),
        )
        return {"error": str(e), "code": "INTERNAL_ERROR"}, 500


@example_entities_bp.route("/by-business-id/<business_id>/at-time", methods=["GET"])
@tag(["example-entities"])
@operation_id("get_example_entity_by_business_id_at_time")
@validate(
    responses={
        200: (ExampleEntityResponse, None),
        404: (ErrorResponse, None),
        400: (ErrorResponse, None),
        500: (ErrorResponse, None),
    }
)
async def get_by_business_id_at_time(business_id: str) -> ResponseReturnValue:
    """Get ExampleEntity by business ID as it existed at a specific point in time"""
    try:
        # Get parameters
        business_id_field = request.args.get("field", "name")
        point_in_time_str = request.args.get("pointInTime")

        if not point_in_time_str:
            return (
                jsonify(
                    {
                        "error": "pointInTime query parameter required (ISO 8601 format)",
                        "code": "MISSING_PARAMETER",
                    }
                ),
                400,
            )

        # Parse datetime
        try:
            point_in_time = datetime.fromisoformat(
                point_in_time_str.replace("Z", "+00:00")
            )
        except ValueError as e:
            return (
                jsonify(
                    {
                        "error": f"Invalid datetime format: {str(e)}",
                        "code": "INVALID_DATETIME",
                    }
                ),
                400,
            )

        result = await service.find_by_business_id_at_time(
            entity_class=ExampleEntity.ENTITY_NAME,
            business_id=business_id,
            business_id_field=business_id_field,
            point_in_time=point_in_time,
            entity_version=str(ExampleEntity.ENTITY_VERSION),
        )

        if not result:
            return {"error": "ExampleEntity not found", "code": "NOT_FOUND"}, 404

        return jsonify(_to_entity_dict(result.data)), 200

    except Exception as e:
        if is_not_found(e):
            return {"error": "ExampleEntity not found", "code": "NOT_FOUND"}, 404
        logger.exception(
            "Error getting ExampleEntity by business ID %s at time: %s",
            business_id,
            str(e),
        )
        return jsonify({"error": str(e)}), 500


@example_entities_bp.route("/at-time", methods=["GET"])
@tag(["example-entities"])
@operation_id("list_example_entities_at_time")
@validate(
    responses={
        200: (ExampleEntityListResponse, None),
        400: (ErrorResponse, None),
        500: (ErrorResponse, None),
    }
)
async def list_entities_at_time() -> ResponseReturnValue:
    """List all ExampleEntities as they existed at a specific point in time"""
    try:
        point_in_time_str = request.args.get("pointInTime")
        if not point_in_time_str:
            return (
                jsonify(
                    {
                        "error": "pointInTime query parameter required (ISO 8601 format)",
                        "code": "MISSING_PARAMETER",
                    }
                ),
                400,
            )

        # Parse datetime
        try:
            point_in_time = datetime.fromisoformat(
                point_in_time_str.replace("Z", "+00:00")
            )
        except ValueError as e:
            return (
                jsonify(
                    {
                        "error": f"Invalid datetime format: {str(e)}",
                        "code": "INVALID_DATETIME",
                    }
                ),
                400,
            )

        results = await service.find_all_at_time(
            entity_class=ExampleEntity.ENTITY_NAME,
            point_in_time=point_in_time,
            entity_version=str(ExampleEntity.ENTITY_VERSION),
        )

        entities = [_to_entity_dict(r.data) for r in results]
        return {"entities": entities, "total": len(entities)}, 200

    except Exception as e:
        logger.exception("Error listing ExampleEntities at time: %s", str(e))
        return {"error": str(e)}, 500


@example_entities_bp.route("/search/at-time", methods=["POST"])
@tag(["example-entities"])
@operation_id("search_example_entities_at_time")
@validate(
    request=SearchRequest,
    responses={
        200: (ExampleEntitySearchResponse, None),
        400: (ValidationErrorResponse, None),
        500: (ErrorResponse, None),
    },
)
async def search_entities_at_time(data: SearchRequest) -> ResponseReturnValue:
    """Search ExampleEntities as they existed at a specific point in time"""
    try:
        point_in_time_str = request.args.get("pointInTime")
        if not point_in_time_str:
            return (
                jsonify(
                    {
                        "error": "pointInTime query parameter required (ISO 8601 format)",
                        "code": "MISSING_PARAMETER",
                    }
                ),
                400,
            )

        # Parse datetime
        try:
            point_in_time = datetime.fromisoformat(
                point_in_time_str.replace("Z", "+00:00")
            )
        except ValueError as e:
            return (
                jsonify(
                    {
                        "error": f"Invalid datetime format: {str(e)}",
                        "code": "INVALID_DATETIME",
                    }
                ),
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
            entity_class=ExampleEntity.ENTITY_NAME,
            condition=search_request,
            point_in_time=point_in_time,
            entity_version=str(ExampleEntity.ENTITY_VERSION),
        )

        entities = [_to_entity_dict(r.data) for r in results]
        return {"entities": entities, "total": len(entities)}, 200

    except Exception as e:
        logger.exception("Error searching ExampleEntities at time: %s", str(e))
        return {"error": str(e)}, 500


@example_entities_bp.route("/count/at-time", methods=["GET"])
@tag(["example-entities"])
@operation_id("count_example_entities_at_time")
@validate(
    responses={
        200: (CountResponse, None),
        400: (ErrorResponse, None),
        500: (ErrorResponse, None),
    }
)
async def count_entities_at_time() -> ResponseReturnValue:
    """Count ExampleEntities as they existed at a specific point in time"""
    try:
        point_in_time_str = request.args.get("pointInTime")
        if not point_in_time_str:
            return (
                jsonify(
                    {
                        "error": "pointInTime query parameter required (ISO 8601 format)",
                        "code": "MISSING_PARAMETER",
                    }
                ),
                400,
            )

        # Parse datetime
        try:
            point_in_time = datetime.fromisoformat(
                point_in_time_str.replace("Z", "+00:00")
            )
        except ValueError as e:
            return (
                jsonify(
                    {
                        "error": f"Invalid datetime format: {str(e)}",
                        "code": "INVALID_DATETIME",
                    }
                ),
                400,
            )

        count = await service.get_entity_count(
            entity_class=ExampleEntity.ENTITY_NAME,
            entity_version=str(ExampleEntity.ENTITY_VERSION),
            point_in_time=point_in_time,
        )

        response = CountResponse(count=count)
        return jsonify(response.model_dump()), 200

    except Exception as e:
        logger.exception("Error counting ExampleEntities at time: %s", str(e))
        return jsonify({"error": str(e)}), 500


@example_entities_bp.route("/<entity_id>/changes", methods=["GET"])
@tag(["example-entities"])
@operation_id("get_example_entity_changes")
@validate(
    responses={
        200: (Dict[str, Any], None),
        404: (ErrorResponse, None),
        500: (ErrorResponse, None),
    }
)
async def get_entity_changes(entity_id: str) -> ResponseReturnValue:
    """Get change history metadata for ExampleEntity"""
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
                    jsonify(
                        {
                            "error": f"Invalid datetime format: {str(e)}",
                            "code": "INVALID_DATETIME",
                        }
                    ),
                    400,
                )

        changes = await service.get_entity_changes_metadata(
            entity_id=entity_id,
            entity_class=ExampleEntity.ENTITY_NAME,
            entity_version=str(ExampleEntity.ENTITY_VERSION),
            point_in_time=point_in_time,
        )

        return jsonify({"entity_id": entity_id, "changes": changes}), 200

    except Exception as e:
        if is_not_found(e):
            return {"error": "ExampleEntity not found", "code": "NOT_FOUND"}, 404
        logger.exception(
            "Error getting changes for ExampleEntity %s: %s", entity_id, str(e)
        )
        return {"error": str(e)}, 500
