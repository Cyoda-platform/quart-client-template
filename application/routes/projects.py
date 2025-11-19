"""
Project Routes for Project Management Application

Manages all Project-related API endpoints including CRUD operations
and workflow transitions as specified in functional requirements.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from quart import Blueprint, jsonify, request
from quart.typing import ResponseReturnValue
from quart_schema import operation_id, tag, validate, validate_querystring
from pydantic import BaseModel

from common.exception import is_not_found
from common.service.entity_service import SearchConditionRequest
from services.services import get_entity_service
from application.entity.project.version_1.project import Project


# Request/Response Models
class ProjectQueryParams(BaseModel):
    status: Optional[str] = None
    priority: Optional[str] = None
    owner_id: Optional[str] = None
    offset: int = 0
    limit: int = 50


class ProjectUpdateQueryParams(BaseModel):
    transition: Optional[str] = None


class ProjectResponse(BaseModel):
    pass  # Will be filled by actual project data


class ProjectListResponse(BaseModel):
    projects: list
    total: int


class ErrorResponse(BaseModel):
    error: str
    code: str


class DeleteResponse(BaseModel):
    success: bool
    message: str
    entity_id: str


# Module-level service proxy
class _ServiceProxy:
    def __getattr__(self, name: str) -> Any:
        return getattr(get_entity_service(), name)


service = _ServiceProxy()
logger = logging.getLogger(__name__)


# Helper to normalize entity data from service
def _to_entity_dict(data: Any) -> Dict[str, Any]:
    return data.model_dump(by_alias=True) if hasattr(data, "model_dump") else data


projects_bp = Blueprint("projects", __name__, url_prefix="/api/projects")


@projects_bp.route("", methods=["POST"])
@tag(["projects"])
@operation_id("create_project")
@validate(
    request=Project,
    responses={
        201: (ProjectResponse, None),
        400: (ErrorResponse, None),
        500: (ErrorResponse, None),
    },
)
async def create_project(data: Project) -> ResponseReturnValue:
    """Create a new Project"""
    try:
        # Convert request to entity data
        entity_data = data.model_dump(by_alias=True)

        # Save the entity
        response = await service.save(
            entity=entity_data,
            entity_class=Project.ENTITY_NAME,
            entity_version=str(Project.ENTITY_VERSION),
        )

        logger.info("Created Project with ID: %s", response.metadata.id)

        # Return created entity
        return _to_entity_dict(response.data), 201

    except ValueError as e:
        logger.warning("Validation error creating Project: %s", str(e))
        return {"error": str(e), "code": "VALIDATION_ERROR"}, 400
    except Exception as e:
        logger.exception("Error creating Project: %s", str(e))
        return {"error": str(e), "code": "INTERNAL_ERROR"}, 500


@projects_bp.route("/<entity_id>", methods=["GET"])
@tag(["projects"])
@operation_id("get_project")
@validate(
    responses={
        200: (ProjectResponse, None),
        404: (ErrorResponse, None),
        400: (ErrorResponse, None),
        500: (ErrorResponse, None),
    }
)
async def get_project(entity_id: str) -> ResponseReturnValue:
    """Get Project by ID"""
    try:
        if not entity_id or len(entity_id.strip()) == 0:
            return {"error": "Entity ID is required", "code": "INVALID_ID"}, 400

        response = await service.get_by_id(
            entity_id=entity_id,
            entity_class=Project.ENTITY_NAME,
            entity_version=str(Project.ENTITY_VERSION),
        )

        if not response:
            return {"error": "Project not found", "code": "NOT_FOUND"}, 404

        return _to_entity_dict(response.data), 200

    except ValueError as e:
        logger.warning("Invalid entity ID %s: %s", entity_id, str(e))
        return {"error": str(e), "code": "INVALID_ID"}, 400
    except Exception as e:
        logger.exception("Error getting Project %s: %s", entity_id, str(e))
        return {"error": str(e), "code": "INTERNAL_ERROR"}, 500


@projects_bp.route("", methods=["GET"])
@validate_querystring(ProjectQueryParams)
@tag(["projects"])
@operation_id("list_projects")
@validate(
    responses={
        200: (ProjectListResponse, None),
        400: (ErrorResponse, None),
        500: (ErrorResponse, None),
    }
)
async def list_projects(query_args: ProjectQueryParams) -> ResponseReturnValue:
    """List Projects with optional filtering"""
    try:
        # Build search conditions
        search_conditions: Dict[str, str] = {}

        if query_args.status:
            search_conditions["status"] = query_args.status
        if query_args.priority:
            search_conditions["priority"] = query_args.priority
        if query_args.owner_id:
            search_conditions["ownerId"] = query_args.owner_id

        # Get entities
        if search_conditions:
            builder = SearchConditionRequest.builder()
            for field, value in search_conditions.items():
                builder.equals(field, value)
            condition = builder.build()

            entities = await service.search(
                entity_class=Project.ENTITY_NAME,
                condition=condition,
                entity_version=str(Project.ENTITY_VERSION),
            )
        else:
            entities = await service.find_all(
                entity_class=Project.ENTITY_NAME,
                entity_version=str(Project.ENTITY_VERSION),
            )

        # Convert to list
        entity_list = [_to_entity_dict(r.data) for r in entities]

        # Apply pagination
        start = query_args.offset
        end = start + query_args.limit
        paginated_entities = entity_list[start:end]

        return jsonify({"projects": paginated_entities, "total": len(entity_list)}), 200

    except Exception as e:
        logger.exception("Error listing Projects: %s", str(e))
        return jsonify({"error": str(e)}), 500


@projects_bp.route("/<entity_id>", methods=["PUT"])
@validate_querystring(ProjectUpdateQueryParams)
@tag(["projects"])
@operation_id("update_project")
@validate(
    request=Project,
    responses={
        200: (ProjectResponse, None),
        404: (ErrorResponse, None),
        400: (ErrorResponse, None),
        500: (ErrorResponse, None),
    },
)
async def update_project(
    entity_id: str, data: Project, query_args: ProjectUpdateQueryParams
) -> ResponseReturnValue:
    """Update Project and optionally trigger workflow transition"""
    try:
        if not entity_id or len(entity_id.strip()) == 0:
            return {"error": "Entity ID is required", "code": "INVALID_ID"}, 400

        # Get transition from query parameters
        transition: Optional[str] = query_args.transition

        # Convert request to entity data
        entity_data: Dict[str, Any] = data.model_dump(by_alias=True)

        # Update the entity
        response = await service.update(
            entity_id=entity_id,
            entity=entity_data,
            entity_class=Project.ENTITY_NAME,
            transition=transition,
            entity_version=str(Project.ENTITY_VERSION),
        )

        logger.info("Updated Project %s", entity_id)

        return jsonify(_to_entity_dict(response.data)), 200

    except ValueError as e:
        logger.warning("Validation error updating Project %s: %s", entity_id, str(e))
        return jsonify({"error": str(e), "code": "VALIDATION_ERROR"}), 400
    except Exception as e:
        logger.exception("Error updating Project %s: %s", entity_id, str(e))
        return jsonify({"error": str(e), "code": "INTERNAL_ERROR"}), 500


@projects_bp.route("/<entity_id>", methods=["DELETE"])
@tag(["projects"])
@operation_id("delete_project")
@validate(
    responses={
        200: (DeleteResponse, None),
        404: (ErrorResponse, None),
        400: (ErrorResponse, None),
        500: (ErrorResponse, None),
    }
)
async def delete_project(entity_id: str) -> ResponseReturnValue:
    """Delete Project"""
    try:
        if not entity_id or len(entity_id.strip()) == 0:
            return {"error": "Entity ID is required", "code": "INVALID_ID"}, 400

        await service.delete_by_id(
            entity_id=entity_id,
            entity_class=Project.ENTITY_NAME,
            entity_version=str(Project.ENTITY_VERSION),
        )

        logger.info("Deleted Project %s", entity_id)

        response = DeleteResponse(
            success=True,
            message="Project deleted successfully",
            entity_id=entity_id,
        )
        return response.model_dump(), 200

    except ValueError as e:
        logger.warning("Invalid entity ID %s: %s", entity_id, str(e))
        return {"error": str(e), "code": "INVALID_ID"}, 400
    except Exception as e:
        logger.exception("Error deleting Project %s: %s", entity_id, str(e))
        return {"error": str(e), "code": "INTERNAL_ERROR"}, 500
