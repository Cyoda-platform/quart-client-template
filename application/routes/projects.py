"""
Project Routes for Project Management Application

Manages all Project-related API endpoints including CRUD operations
and project management functionality.
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from quart import Blueprint, request
from quart.typing import ResponseReturnValue

from application.entity.project.version_1.project import Project
from services.services import get_entity_service


# Module-level service instance
class _ServiceProxy:
    def __getattr__(self, name: str) -> Any:
        return getattr(get_entity_service(), name)


service = _ServiceProxy()
logger = logging.getLogger(__name__)


def _to_entity_dict(data: Any) -> Dict[str, Any]:
    return data.model_dump(by_alias=True) if hasattr(data, "model_dump") else data


projects_bp = Blueprint("projects", __name__, url_prefix="/api/projects")


@projects_bp.route("", methods=["POST"])
async def create_project() -> ResponseReturnValue:
    """Create a new Project"""
    try:
        data = await request.get_json()
        if not data:
            return {"error": "Request body is required", "code": "INVALID_REQUEST"}, 400

        project = Project(**data)
        entity_data = project.model_dump(by_alias=True)

        response = await service.save(
            entity=entity_data,
            entity_class=Project.ENTITY_NAME,
            entity_version=str(Project.ENTITY_VERSION),
        )

        logger.info("Created Project with ID: %s", response.metadata.id)
        return _to_entity_dict(response.data), 201

    except ValueError as e:
        logger.warning("Validation error creating Project: %s", str(e))
        return {"error": str(e), "code": "VALIDATION_ERROR"}, 400
    except Exception as e:
        logger.exception("Error creating Project: %s", str(e))
        return {"error": str(e), "code": "INTERNAL_ERROR"}, 500


@projects_bp.route("/<entity_id>", methods=["GET"])
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

    except Exception as e:
        logger.exception("Error getting Project: %s", str(e))
        return {"error": str(e), "code": "INTERNAL_ERROR"}, 500


@projects_bp.route("", methods=["GET"])
async def list_projects() -> ResponseReturnValue:
    """List Projects with optional filtering"""
    try:
        owner_id = request.args.get("owner_id")
        status = request.args.get("status")
        limit = int(request.args.get("limit", 50))
        offset = int(request.args.get("offset", 0))

        conditions = []
        if owner_id:
            conditions.append(
                {"field": "owner_id", "operator": "EQUALS", "value": owner_id}
            )
        if status:
            conditions.append({"field": "state", "operator": "EQUALS", "value": status})

        response = await service.search(
            entity_class=Project.ENTITY_NAME,
            entity_version=str(Project.ENTITY_VERSION),
            conditions=conditions,
            limit=limit,
            offset=offset,
        )

        projects = []
        if response and response.entities:
            projects = [_to_entity_dict(entity) for entity in response.entities]

        return {
            "projects": projects,
            "total": len(projects),
            "limit": limit,
            "offset": offset,
        }, 200

    except Exception as e:
        logger.exception("Error listing Projects: %s", str(e))
        return {"error": str(e), "code": "INTERNAL_ERROR"}, 500


@projects_bp.route("/<entity_id>", methods=["PUT"])
async def update_project(entity_id: str) -> ResponseReturnValue:
    """Update Project by ID"""
    try:
        if not entity_id or len(entity_id.strip()) == 0:
            return {"error": "Entity ID is required", "code": "INVALID_ID"}, 400

        data = await request.get_json()
        if not data:
            return {"error": "Request body is required", "code": "INVALID_REQUEST"}, 400

        existing_response = await service.get_by_id(
            entity_id=entity_id,
            entity_class=Project.ENTITY_NAME,
            entity_version=str(Project.ENTITY_VERSION),
        )

        if not existing_response:
            return {"error": "Project not found", "code": "NOT_FOUND"}, 404

        existing_data = _to_entity_dict(existing_response.data)
        existing_data.update(data)

        project = Project(**existing_data)
        entity_data = project.model_dump(by_alias=True)

        response = await service.save(
            entity=entity_data,
            entity_class=Project.ENTITY_NAME,
            entity_version=str(Project.ENTITY_VERSION),
        )

        logger.info("Updated Project with ID: %s", entity_id)
        return _to_entity_dict(response.data), 200

    except ValueError as e:
        logger.warning("Validation error updating Project: %s", str(e))
        return {"error": str(e), "code": "VALIDATION_ERROR"}, 400
    except Exception as e:
        logger.exception("Error updating Project: %s", str(e))
        return {"error": str(e), "code": "INTERNAL_ERROR"}, 500


@projects_bp.route("/<entity_id>", methods=["DELETE"])
async def delete_project(entity_id: str) -> ResponseReturnValue:
    """Delete Project by ID"""
    try:
        if not entity_id or len(entity_id.strip()) == 0:
            return {"error": "Entity ID is required", "code": "INVALID_ID"}, 400

        existing_response = await service.get_by_id(
            entity_id=entity_id,
            entity_class=Project.ENTITY_NAME,
            entity_version=str(Project.ENTITY_VERSION),
        )

        if not existing_response:
            return {"error": "Project not found", "code": "NOT_FOUND"}, 404

        await service.delete(
            entity_id=entity_id,
            entity_class=Project.ENTITY_NAME,
            entity_version=str(Project.ENTITY_VERSION),
        )

        logger.info("Deleted Project with ID: %s", entity_id)
        return {"message": "Project deleted successfully"}, 200

    except Exception as e:
        logger.exception("Error deleting Project: %s", str(e))
        return {"error": str(e), "code": "INTERNAL_ERROR"}, 500


@projects_bp.route("/<entity_id>/transition", methods=["POST"])
async def transition_project(entity_id: str) -> ResponseReturnValue:
    """Transition Project state"""
    try:
        if not entity_id or len(entity_id.strip()) == 0:
            return {"error": "Entity ID is required", "code": "INVALID_ID"}, 400

        data = await request.get_json()
        if not data or "transition" not in data:
            return {
                "error": "Transition name is required",
                "code": "INVALID_REQUEST",
            }, 400

        transition_name = data["transition"]

        response = await service.transition(
            entity_id=entity_id,
            entity_class=Project.ENTITY_NAME,
            entity_version=str(Project.ENTITY_VERSION),
            transition_name=transition_name,
        )

        logger.info(
            "Transitioned Project %s with transition: %s", entity_id, transition_name
        )
        return _to_entity_dict(response.data), 200

    except Exception as e:
        logger.exception("Error transitioning Project: %s", str(e))
        return {"error": str(e), "code": "INTERNAL_ERROR"}, 500


@projects_bp.route("/<entity_id>/tasks", methods=["GET"])
async def get_project_tasks(entity_id: str) -> ResponseReturnValue:
    """Get all tasks for a project"""
    try:
        if not entity_id or len(entity_id.strip()) == 0:
            return {"error": "Entity ID is required", "code": "INVALID_ID"}, 400

        # Get tasks for this project
        response = await service.search(
            entity_class="Task",
            entity_version="1",
            conditions=[
                {"field": "project_id", "operator": "EQUALS", "value": entity_id}
            ],
        )

        tasks = []
        if response and response.entities:
            tasks = [_to_entity_dict(entity) for entity in response.entities]

        return {"tasks": tasks, "total": len(tasks)}, 200

    except Exception as e:
        logger.exception("Error getting project tasks: %s", str(e))
        return {"error": str(e), "code": "INTERNAL_ERROR"}, 500
