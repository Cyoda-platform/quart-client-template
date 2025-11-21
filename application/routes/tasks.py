"""
Task Routes for Project Management Application

Manages all Task-related API endpoints including CRUD operations,
state transitions, and task management functionality.
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from quart import Blueprint, request
from quart.typing import ResponseReturnValue

from application.entity.task.version_1.task import Task
from services.services import get_entity_service


# Module-level service instance
class _ServiceProxy:
    def __getattr__(self, name: str) -> Any:
        return getattr(get_entity_service(), name)


service = _ServiceProxy()
logger = logging.getLogger(__name__)


def _to_entity_dict(data: Any) -> Dict[str, Any]:
    return data.model_dump(by_alias=True) if hasattr(data, "model_dump") else data


tasks_bp = Blueprint("tasks", __name__, url_prefix="/api/tasks")


@tasks_bp.route("", methods=["POST"])
async def create_task() -> ResponseReturnValue:
    """Create a new Task"""
    try:
        data = await request.get_json()
        if not data:
            return {"error": "Request body is required", "code": "INVALID_REQUEST"}, 400

        task = Task(**data)
        entity_data = task.model_dump(by_alias=True)

        response = await service.save(
            entity=entity_data,
            entity_class=Task.ENTITY_NAME,
            entity_version=str(Task.ENTITY_VERSION),
        )

        logger.info("Created Task with ID: %s", response.metadata.id)
        return _to_entity_dict(response.data), 201

    except ValueError as e:
        logger.warning("Validation error creating Task: %s", str(e))
        return {"error": str(e), "code": "VALIDATION_ERROR"}, 400
    except Exception as e:
        logger.exception("Error creating Task: %s", str(e))
        return {"error": str(e), "code": "INTERNAL_ERROR"}, 500


@tasks_bp.route("/<entity_id>", methods=["GET"])
async def get_task(entity_id: str) -> ResponseReturnValue:
    """Get Task by ID"""
    try:
        if not entity_id or len(entity_id.strip()) == 0:
            return {"error": "Entity ID is required", "code": "INVALID_ID"}, 400

        response = await service.get_by_id(
            entity_id=entity_id,
            entity_class=Task.ENTITY_NAME,
            entity_version=str(Task.ENTITY_VERSION),
        )

        if not response:
            return {"error": "Task not found", "code": "NOT_FOUND"}, 404

        return _to_entity_dict(response.data), 200

    except Exception as e:
        logger.exception("Error getting Task: %s", str(e))
        return {"error": str(e), "code": "INTERNAL_ERROR"}, 500


@tasks_bp.route("", methods=["GET"])
async def list_tasks() -> ResponseReturnValue:
    """List Tasks with filtering"""
    try:
        project_id = request.args.get("project_id")
        assignee_id = request.args.get("assignee_id")
        status = request.args.get("status")
        priority = request.args.get("priority")
        due_date_before = request.args.get("due_date_before")
        limit = int(request.args.get("limit", 50))
        offset = int(request.args.get("offset", 0))

        conditions = []
        if project_id:
            conditions.append(
                {"field": "project_id", "operator": "EQUALS", "value": project_id}
            )
        if assignee_id:
            conditions.append(
                {"field": "assignee_id", "operator": "EQUALS", "value": assignee_id}
            )
        if status:
            conditions.append({"field": "state", "operator": "EQUALS", "value": status})
        if priority:
            conditions.append(
                {"field": "priority", "operator": "EQUALS", "value": priority}
            )
        if due_date_before:
            conditions.append(
                {"field": "due_date", "operator": "LESS_THAN", "value": due_date_before}
            )

        response = await service.search(
            entity_class=Task.ENTITY_NAME,
            entity_version=str(Task.ENTITY_VERSION),
            conditions=conditions,
            limit=limit,
            offset=offset,
        )

        tasks = []
        if response and response.entities:
            tasks = [_to_entity_dict(entity) for entity in response.entities]

        return {
            "tasks": tasks,
            "total": len(tasks),
            "limit": limit,
            "offset": offset,
        }, 200

    except Exception as e:
        logger.exception("Error listing Tasks: %s", str(e))
        return {"error": str(e), "code": "INTERNAL_ERROR"}, 500


@tasks_bp.route("/<entity_id>", methods=["PUT"])
async def update_task(entity_id: str) -> ResponseReturnValue:
    """Update Task by ID"""
    try:
        if not entity_id or len(entity_id.strip()) == 0:
            return {"error": "Entity ID is required", "code": "INVALID_ID"}, 400

        data = await request.get_json()
        if not data:
            return {"error": "Request body is required", "code": "INVALID_REQUEST"}, 400

        existing_response = await service.get_by_id(
            entity_id=entity_id,
            entity_class=Task.ENTITY_NAME,
            entity_version=str(Task.ENTITY_VERSION),
        )

        if not existing_response:
            return {"error": "Task not found", "code": "NOT_FOUND"}, 404

        existing_data = _to_entity_dict(existing_response.data)
        existing_data.update(data)

        task = Task(**existing_data)
        entity_data = task.model_dump(by_alias=True)

        response = await service.save(
            entity=entity_data,
            entity_class=Task.ENTITY_NAME,
            entity_version=str(Task.ENTITY_VERSION),
        )

        logger.info("Updated Task with ID: %s", entity_id)
        return _to_entity_dict(response.data), 200

    except ValueError as e:
        logger.warning("Validation error updating Task: %s", str(e))
        return {"error": str(e), "code": "VALIDATION_ERROR"}, 400
    except Exception as e:
        logger.exception("Error updating Task: %s", str(e))
        return {"error": str(e), "code": "INTERNAL_ERROR"}, 500


@tasks_bp.route("/<entity_id>", methods=["DELETE"])
async def delete_task(entity_id: str) -> ResponseReturnValue:
    """Delete Task by ID"""
    try:
        if not entity_id or len(entity_id.strip()) == 0:
            return {"error": "Entity ID is required", "code": "INVALID_ID"}, 400

        existing_response = await service.get_by_id(
            entity_id=entity_id,
            entity_class=Task.ENTITY_NAME,
            entity_version=str(Task.ENTITY_VERSION),
        )

        if not existing_response:
            return {"error": "Task not found", "code": "NOT_FOUND"}, 404

        await service.delete(
            entity_id=entity_id,
            entity_class=Task.ENTITY_NAME,
            entity_version=str(Task.ENTITY_VERSION),
        )

        logger.info("Deleted Task with ID: %s", entity_id)
        return {"message": "Task deleted successfully"}, 200

    except Exception as e:
        logger.exception("Error deleting Task: %s", str(e))
        return {"error": str(e), "code": "INTERNAL_ERROR"}, 500


@tasks_bp.route("/<entity_id>/transition", methods=["POST"])
async def transition_task(entity_id: str) -> ResponseReturnValue:
    """Transition Task state"""
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
        user_id = data.get("user_id")  # For permission checking

        # Add user context for criteria evaluation
        context = {}
        if user_id:
            context["user_id"] = user_id

        response = await service.transition(
            entity_id=entity_id,
            entity_class=Task.ENTITY_NAME,
            entity_version=str(Task.ENTITY_VERSION),
            transition_name=transition_name,
            context=context,
        )

        logger.info(
            "Transitioned Task %s with transition: %s", entity_id, transition_name
        )
        return _to_entity_dict(response.data), 200

    except Exception as e:
        logger.exception("Error transitioning Task: %s", str(e))
        return {"error": str(e), "code": "INTERNAL_ERROR"}, 500
