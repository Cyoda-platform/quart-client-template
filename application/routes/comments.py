"""
Comment Routes for Project Management Application

Manages all Comment-related API endpoints including CRUD operations
and comment functionality.
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from quart import Blueprint, request
from quart.typing import ResponseReturnValue

from application.entity.comment.version_1.comment import Comment
from services.services import get_entity_service


class _ServiceProxy:
    def __getattr__(self, name: str) -> Any:
        return getattr(get_entity_service(), name)


service = _ServiceProxy()
logger = logging.getLogger(__name__)


def _to_entity_dict(data: Any) -> Dict[str, Any]:
    return data.model_dump(by_alias=True) if hasattr(data, "model_dump") else data


comments_bp = Blueprint("comments", __name__, url_prefix="/api/comments")


@comments_bp.route("", methods=["POST"])
async def create_comment() -> ResponseReturnValue:
    """Create a new Comment"""
    try:
        data = await request.get_json()
        if not data:
            return {"error": "Request body is required", "code": "INVALID_REQUEST"}, 400

        comment = Comment(**data)
        entity_data = comment.model_dump(by_alias=True)

        response = await service.save(
            entity=entity_data,
            entity_class=Comment.ENTITY_NAME,
            entity_version=str(Comment.ENTITY_VERSION),
        )

        logger.info("Created Comment with ID: %s", response.metadata.id)
        return _to_entity_dict(response.data), 201

    except ValueError as e:
        logger.warning("Validation error creating Comment: %s", str(e))
        return {"error": str(e), "code": "VALIDATION_ERROR"}, 400
    except Exception as e:
        logger.exception("Error creating Comment: %s", str(e))
        return {"error": str(e), "code": "INTERNAL_ERROR"}, 500


@comments_bp.route("/<entity_id>", methods=["GET"])
async def get_comment(entity_id: str) -> ResponseReturnValue:
    """Get Comment by ID"""
    try:
        if not entity_id or len(entity_id.strip()) == 0:
            return {"error": "Entity ID is required", "code": "INVALID_ID"}, 400

        response = await service.get_by_id(
            entity_id=entity_id,
            entity_class=Comment.ENTITY_NAME,
            entity_version=str(Comment.ENTITY_VERSION),
        )

        if not response:
            return {"error": "Comment not found", "code": "NOT_FOUND"}, 404

        return _to_entity_dict(response.data), 200

    except Exception as e:
        logger.exception("Error getting Comment: %s", str(e))
        return {"error": str(e), "code": "INTERNAL_ERROR"}, 500


@comments_bp.route("", methods=["GET"])
async def list_comments() -> ResponseReturnValue:
    """List Comments with filtering"""
    try:
        task_id = request.args.get("task_id")
        author_id = request.args.get("author_id")
        limit = int(request.args.get("limit", 50))
        offset = int(request.args.get("offset", 0))

        conditions = []
        if task_id:
            conditions.append(
                {"field": "task_id", "operator": "EQUALS", "value": task_id}
            )
        if author_id:
            conditions.append(
                {"field": "author_id", "operator": "EQUALS", "value": author_id}
            )

        response = await service.search(
            entity_class=Comment.ENTITY_NAME,
            entity_version=str(Comment.ENTITY_VERSION),
            conditions=conditions,
            limit=limit,
            offset=offset,
        )

        comments = []
        if response and response.entities:
            comments = [_to_entity_dict(entity) for entity in response.entities]

        return {
            "comments": comments,
            "total": len(comments),
            "limit": limit,
            "offset": offset,
        }, 200

    except Exception as e:
        logger.exception("Error listing Comments: %s", str(e))
        return {"error": str(e), "code": "INTERNAL_ERROR"}, 500


@comments_bp.route("/<entity_id>", methods=["PUT"])
async def update_comment(entity_id: str) -> ResponseReturnValue:
    """Update Comment by ID"""
    try:
        if not entity_id or len(entity_id.strip()) == 0:
            return {"error": "Entity ID is required", "code": "INVALID_ID"}, 400

        data = await request.get_json()
        if not data:
            return {"error": "Request body is required", "code": "INVALID_REQUEST"}, 400

        existing_response = await service.get_by_id(
            entity_id=entity_id,
            entity_class=Comment.ENTITY_NAME,
            entity_version=str(Comment.ENTITY_VERSION),
        )

        if not existing_response:
            return {"error": "Comment not found", "code": "NOT_FOUND"}, 404

        existing_data = _to_entity_dict(existing_response.data)
        existing_data.update(data)

        comment = Comment(**existing_data)
        entity_data = comment.model_dump(by_alias=True)

        response = await service.save(
            entity=entity_data,
            entity_class=Comment.ENTITY_NAME,
            entity_version=str(Comment.ENTITY_VERSION),
        )

        logger.info("Updated Comment with ID: %s", entity_id)
        return _to_entity_dict(response.data), 200

    except ValueError as e:
        logger.warning("Validation error updating Comment: %s", str(e))
        return {"error": str(e), "code": "VALIDATION_ERROR"}, 400
    except Exception as e:
        logger.exception("Error updating Comment: %s", str(e))
        return {"error": str(e), "code": "INTERNAL_ERROR"}, 500


@comments_bp.route("/<entity_id>/transition", methods=["POST"])
async def transition_comment(entity_id: str) -> ResponseReturnValue:
    """Transition Comment state"""
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
            entity_class=Comment.ENTITY_NAME,
            entity_version=str(Comment.ENTITY_VERSION),
            transition_name=transition_name,
        )

        logger.info(
            "Transitioned Comment %s with transition: %s", entity_id, transition_name
        )
        return _to_entity_dict(response.data), 200

    except Exception as e:
        logger.exception("Error transitioning Comment: %s", str(e))
        return {"error": str(e), "code": "INTERNAL_ERROR"}, 500


# Special endpoint for task comments
@comments_bp.route("/task/<task_id>", methods=["GET"])
async def get_task_comments(task_id: str) -> ResponseReturnValue:
    """Get all comments for a task"""
    try:
        if not task_id or len(task_id.strip()) == 0:
            return {"error": "Task ID is required", "code": "INVALID_ID"}, 400

        response = await service.search(
            entity_class=Comment.ENTITY_NAME,
            entity_version=str(Comment.ENTITY_VERSION),
            conditions=[{"field": "task_id", "operator": "EQUALS", "value": task_id}],
        )

        comments = []
        if response and response.entities:
            comments = [_to_entity_dict(entity) for entity in response.entities]

        return {"comments": comments, "total": len(comments)}, 200

    except Exception as e:
        logger.exception("Error getting task comments: %s", str(e))
        return {"error": str(e), "code": "INTERNAL_ERROR"}, 500
