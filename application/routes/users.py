"""
User Routes for Project Management Application

Manages all User-related API endpoints including CRUD operations
and user management functionality.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from quart import Blueprint, jsonify, request
from quart.typing import ResponseReturnValue

from common.exception import is_not_found
from services.services import get_entity_service
from application.entity.user.version_1.user import User

# Module-level service instance to avoid repeated lookups
class _ServiceProxy:
    def __getattr__(self, name: str) -> Any:
        return getattr(get_entity_service(), name)

service = _ServiceProxy()
logger = logging.getLogger(__name__)

# Helper to normalize entity data from service
def _to_entity_dict(data: Any) -> Dict[str, Any]:
    return data.model_dump(by_alias=True) if hasattr(data, "model_dump") else data

users_bp = Blueprint("users", __name__, url_prefix="/api/users")

# ---- Routes -----------------------------------------------------------------

@users_bp.route("", methods=["POST"])
async def create_user() -> ResponseReturnValue:
    """Create a new User"""
    try:
        data = await request.get_json()
        if not data:
            return {"error": "Request body is required", "code": "INVALID_REQUEST"}, 400

        # Validate using Pydantic model
        user = User(**data)
        entity_data = user.model_dump(by_alias=True)

        # Save the entity
        response = await service.save(
            entity=entity_data,
            entity_class=User.ENTITY_NAME,
            entity_version=str(User.ENTITY_VERSION),
        )

        logger.info("Created User with ID: %s", response.metadata.id)
        return _to_entity_dict(response.data), 201

    except ValueError as e:
        logger.warning("Validation error creating User: %s", str(e))
        return {"error": str(e), "code": "VALIDATION_ERROR"}, 400
    except Exception as e:
        logger.exception("Error creating User: %s", str(e))
        return {"error": str(e), "code": "INTERNAL_ERROR"}, 500

@users_bp.route("/<entity_id>", methods=["GET"])
async def get_user(entity_id: str) -> ResponseReturnValue:
    """Get User by ID"""
    try:
        if not entity_id or len(entity_id.strip()) == 0:
            return {"error": "Entity ID is required", "code": "INVALID_ID"}, 400

        response = await service.get_by_id(
            entity_id=entity_id,
            entity_class=User.ENTITY_NAME,
            entity_version=str(User.ENTITY_VERSION),
        )

        if not response:
            return {"error": "User not found", "code": "NOT_FOUND"}, 404

        return _to_entity_dict(response.data), 200

    except Exception as e:
        logger.exception("Error getting User: %s", str(e))
        return {"error": str(e), "code": "INTERNAL_ERROR"}, 500

@users_bp.route("", methods=["GET"])
async def list_users() -> ResponseReturnValue:
    """List Users with optional filtering"""
    try:
        # Get query parameters
        role = request.args.get("role")
        is_active = request.args.get("is_active")
        limit = int(request.args.get("limit", 50))
        offset = int(request.args.get("offset", 0))

        # Build search conditions
        conditions = []
        if role:
            conditions.append({
                "field": "role",
                "operator": "EQUALS",
                "value": role
            })
        if is_active is not None:
            conditions.append({
                "field": "isActive",
                "operator": "EQUALS",
                "value": "true" if is_active.lower() == "true" else "false"
            })

        # Search users
        response = await service.search(
            entity_class=User.ENTITY_NAME,
            entity_version=str(User.ENTITY_VERSION),
            conditions=conditions,
            limit=limit,
            offset=offset
        )

        users = []
        if response and response.entities:
            users = [_to_entity_dict(entity) for entity in response.entities]

        return {
            "users": users,
            "total": len(users),
            "limit": limit,
            "offset": offset
        }, 200

    except Exception as e:
        logger.exception("Error listing Users: %s", str(e))
        return {"error": str(e), "code": "INTERNAL_ERROR"}, 500

@users_bp.route("/<entity_id>", methods=["PUT"])
async def update_user(entity_id: str) -> ResponseReturnValue:
    """Update User by ID"""
    try:
        if not entity_id or len(entity_id.strip()) == 0:
            return {"error": "Entity ID is required", "code": "INVALID_ID"}, 400

        data = await request.get_json()
        if not data:
            return {"error": "Request body is required", "code": "INVALID_REQUEST"}, 400

        # Get existing user
        existing_response = await service.get_by_id(
            entity_id=entity_id,
            entity_class=User.ENTITY_NAME,
            entity_version=str(User.ENTITY_VERSION),
        )

        if not existing_response:
            return {"error": "User not found", "code": "NOT_FOUND"}, 404

        # Merge with existing data
        existing_data = _to_entity_dict(existing_response.data)
        existing_data.update(data)

        # Validate using Pydantic model
        user = User(**existing_data)
        entity_data = user.model_dump(by_alias=True)

        # Save the updated entity
        response = await service.save(
            entity=entity_data,
            entity_class=User.ENTITY_NAME,
            entity_version=str(User.ENTITY_VERSION),
        )

        logger.info("Updated User with ID: %s", entity_id)
        return _to_entity_dict(response.data), 200

    except ValueError as e:
        logger.warning("Validation error updating User: %s", str(e))
        return {"error": str(e), "code": "VALIDATION_ERROR"}, 400
    except Exception as e:
        logger.exception("Error updating User: %s", str(e))
        return {"error": str(e), "code": "INTERNAL_ERROR"}, 500

@users_bp.route("/<entity_id>", methods=["DELETE"])
async def delete_user(entity_id: str) -> ResponseReturnValue:
    """Delete User by ID"""
    try:
        if not entity_id or len(entity_id.strip()) == 0:
            return {"error": "Entity ID is required", "code": "INVALID_ID"}, 400

        # Check if user exists
        existing_response = await service.get_by_id(
            entity_id=entity_id,
            entity_class=User.ENTITY_NAME,
            entity_version=str(User.ENTITY_VERSION),
        )

        if not existing_response:
            return {"error": "User not found", "code": "NOT_FOUND"}, 404

        # Delete the user
        await service.delete(
            entity_id=entity_id,
            entity_class=User.ENTITY_NAME,
            entity_version=str(User.ENTITY_VERSION),
        )

        logger.info("Deleted User with ID: %s", entity_id)
        return {"message": "User deleted successfully"}, 200

    except Exception as e:
        logger.exception("Error deleting User: %s", str(e))
        return {"error": str(e), "code": "INTERNAL_ERROR"}, 500

@users_bp.route("/<entity_id>/transition", methods=["POST"])
async def transition_user(entity_id: str) -> ResponseReturnValue:
    """Transition User state"""
    try:
        if not entity_id or len(entity_id.strip()) == 0:
            return {"error": "Entity ID is required", "code": "INVALID_ID"}, 400

        data = await request.get_json()
        if not data or "transition" not in data:
            return {"error": "Transition name is required", "code": "INVALID_REQUEST"}, 400

        transition_name = data["transition"]

        # Perform transition
        response = await service.transition(
            entity_id=entity_id,
            entity_class=User.ENTITY_NAME,
            entity_version=str(User.ENTITY_VERSION),
            transition_name=transition_name,
        )

        logger.info("Transitioned User %s with transition: %s", entity_id, transition_name)
        return _to_entity_dict(response.data), 200

    except Exception as e:
        logger.exception("Error transitioning User: %s", str(e))
        return {"error": str(e), "code": "INTERNAL_ERROR"}, 500
