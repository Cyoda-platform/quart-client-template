"""
TimeEntry Routes for Project Management Application

Manages all TimeEntry-related API endpoints including CRUD operations
and time tracking functionality.
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from quart import Blueprint, request
from quart.typing import ResponseReturnValue

from services.services import get_entity_service
from application.entity.time_entry.version_1.time_entry import TimeEntry

class _ServiceProxy:
    def __getattr__(self, name: str) -> Any:
        return getattr(get_entity_service(), name)

service = _ServiceProxy()
logger = logging.getLogger(__name__)

def _to_entity_dict(data: Any) -> Dict[str, Any]:
    return data.model_dump(by_alias=True) if hasattr(data, "model_dump") else data

time_entries_bp = Blueprint("time_entries", __name__, url_prefix="/api/time-entries")

@time_entries_bp.route("", methods=["POST"])
async def create_time_entry() -> ResponseReturnValue:
    """Create a new TimeEntry"""
    try:
        data = await request.get_json()
        if not data:
            return {"error": "Request body is required", "code": "INVALID_REQUEST"}, 400

        time_entry = TimeEntry(**data)
        entity_data = time_entry.model_dump(by_alias=True)

        response = await service.save(
            entity=entity_data,
            entity_class=TimeEntry.ENTITY_NAME,
            entity_version=str(TimeEntry.ENTITY_VERSION),
        )

        logger.info("Created TimeEntry with ID: %s", response.metadata.id)
        return _to_entity_dict(response.data), 201

    except ValueError as e:
        logger.warning("Validation error creating TimeEntry: %s", str(e))
        return {"error": str(e), "code": "VALIDATION_ERROR"}, 400
    except Exception as e:
        logger.exception("Error creating TimeEntry: %s", str(e))
        return {"error": str(e), "code": "INTERNAL_ERROR"}, 500

@time_entries_bp.route("/<entity_id>", methods=["GET"])
async def get_time_entry(entity_id: str) -> ResponseReturnValue:
    """Get TimeEntry by ID"""
    try:
        if not entity_id or len(entity_id.strip()) == 0:
            return {"error": "Entity ID is required", "code": "INVALID_ID"}, 400

        response = await service.get_by_id(
            entity_id=entity_id,
            entity_class=TimeEntry.ENTITY_NAME,
            entity_version=str(TimeEntry.ENTITY_VERSION),
        )

        if not response:
            return {"error": "TimeEntry not found", "code": "NOT_FOUND"}, 404

        return _to_entity_dict(response.data), 200

    except Exception as e:
        logger.exception("Error getting TimeEntry: %s", str(e))
        return {"error": str(e), "code": "INTERNAL_ERROR"}, 500

@time_entries_bp.route("", methods=["GET"])
async def list_time_entries() -> ResponseReturnValue:
    """List TimeEntries with filtering"""
    try:
        task_id = request.args.get("task_id")
        user_id = request.args.get("user_id")
        start_date = request.args.get("start_date")
        end_date = request.args.get("end_date")
        limit = int(request.args.get("limit", 50))
        offset = int(request.args.get("offset", 0))

        conditions = []
        if task_id:
            conditions.append({
                "field": "task_id",
                "operator": "EQUALS",
                "value": task_id
            })
        if user_id:
            conditions.append({
                "field": "user_id",
                "operator": "EQUALS",
                "value": user_id
            })
        if start_date:
            conditions.append({
                "field": "start_time",
                "operator": "GREATER_OR_EQUAL",
                "value": start_date
            })
        if end_date:
            conditions.append({
                "field": "start_time",
                "operator": "LESS_OR_EQUAL",
                "value": end_date
            })

        response = await service.search(
            entity_class=TimeEntry.ENTITY_NAME,
            entity_version=str(TimeEntry.ENTITY_VERSION),
            conditions=conditions,
            limit=limit,
            offset=offset
        )

        time_entries = []
        if response and response.entities:
            time_entries = [_to_entity_dict(entity) for entity in response.entities]

        return {
            "time_entries": time_entries,
            "total": len(time_entries),
            "limit": limit,
            "offset": offset
        }, 200

    except Exception as e:
        logger.exception("Error listing TimeEntries: %s", str(e))
        return {"error": str(e), "code": "INTERNAL_ERROR"}, 500

@time_entries_bp.route("/<entity_id>", methods=["PUT"])
async def update_time_entry(entity_id: str) -> ResponseReturnValue:
    """Update TimeEntry by ID"""
    try:
        if not entity_id or len(entity_id.strip()) == 0:
            return {"error": "Entity ID is required", "code": "INVALID_ID"}, 400

        data = await request.get_json()
        if not data:
            return {"error": "Request body is required", "code": "INVALID_REQUEST"}, 400

        existing_response = await service.get_by_id(
            entity_id=entity_id,
            entity_class=TimeEntry.ENTITY_NAME,
            entity_version=str(TimeEntry.ENTITY_VERSION),
        )

        if not existing_response:
            return {"error": "TimeEntry not found", "code": "NOT_FOUND"}, 404

        existing_data = _to_entity_dict(existing_response.data)
        existing_data.update(data)

        time_entry = TimeEntry(**existing_data)
        entity_data = time_entry.model_dump(by_alias=True)

        response = await service.save(
            entity=entity_data,
            entity_class=TimeEntry.ENTITY_NAME,
            entity_version=str(TimeEntry.ENTITY_VERSION),
        )

        logger.info("Updated TimeEntry with ID: %s", entity_id)
        return _to_entity_dict(response.data), 200

    except ValueError as e:
        logger.warning("Validation error updating TimeEntry: %s", str(e))
        return {"error": str(e), "code": "VALIDATION_ERROR"}, 400
    except Exception as e:
        logger.exception("Error updating TimeEntry: %s", str(e))
        return {"error": str(e), "code": "INTERNAL_ERROR"}, 500

@time_entries_bp.route("/<entity_id>/transition", methods=["POST"])
async def transition_time_entry(entity_id: str) -> ResponseReturnValue:
    """Transition TimeEntry state"""
    try:
        if not entity_id or len(entity_id.strip()) == 0:
            return {"error": "Entity ID is required", "code": "INVALID_ID"}, 400

        data = await request.get_json()
        if not data or "transition" not in data:
            return {"error": "Transition name is required", "code": "INVALID_REQUEST"}, 400

        transition_name = data["transition"]

        response = await service.transition(
            entity_id=entity_id,
            entity_class=TimeEntry.ENTITY_NAME,
            entity_version=str(TimeEntry.ENTITY_VERSION),
            transition_name=transition_name,
        )

        logger.info("Transitioned TimeEntry %s with transition: %s", entity_id, transition_name)
        return _to_entity_dict(response.data), 200

    except Exception as e:
        logger.exception("Error transitioning TimeEntry: %s", str(e))
        return {"error": str(e), "code": "INTERNAL_ERROR"}, 500

# Special endpoint for task time entries
@time_entries_bp.route("/task/<task_id>", methods=["GET"])
async def get_task_time_entries(task_id: str) -> ResponseReturnValue:
    """Get all time entries for a task"""
    try:
        if not task_id or len(task_id.strip()) == 0:
            return {"error": "Task ID is required", "code": "INVALID_ID"}, 400

        response = await service.search(
            entity_class=TimeEntry.ENTITY_NAME,
            entity_version=str(TimeEntry.ENTITY_VERSION),
            conditions=[{
                "field": "task_id",
                "operator": "EQUALS",
                "value": task_id
            }]
        )

        time_entries = []
        total_hours = 0.0
        if response and response.entities:
            for entity in response.entities:
                entry_dict = _to_entity_dict(entity)
                time_entries.append(entry_dict)
                duration_minutes = entry_dict.get("duration_minutes", 0)
                total_hours += duration_minutes / 60.0

        return {
            "time_entries": time_entries,
            "total": len(time_entries),
            "total_hours": round(total_hours, 2)
        }, 200

    except Exception as e:
        logger.exception("Error getting task time entries: %s", str(e))
        return {"error": str(e), "code": "INTERNAL_ERROR"}, 500
