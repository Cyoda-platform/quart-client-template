"""
Customer Routes for Cyoda Client Application

Manages all Customer-related API endpoints including CRUD operations
and workflow transitions following the thin proxy pattern.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from quart import Blueprint, jsonify, request
from quart.typing import ResponseReturnValue

from application.entity.customer.version_1.customer import Customer
from common.service.entity_service import SearchConditionRequest
from services.services import get_entity_service


# Module-level service instance to avoid repeated lookups
# Lazy proxy to avoid initializing services at import time
class _ServiceProxy:
    def __getattr__(self, name: str) -> Any:
        return getattr(get_entity_service(), name)


service = _ServiceProxy()
logger = logging.getLogger(__name__)


# Helper to normalize entity data from service (Pydantic model or dict)
def _to_entity_dict(data: Any) -> Dict[str, Any]:
    return data.model_dump(by_alias=True) if hasattr(data, "model_dump") else data


customer_bp = Blueprint("customers", __name__, url_prefix="/api/customers")

# ---- Routes -----------------------------------------------------------------


@customer_bp.route("", methods=["POST"])
async def create_customer() -> ResponseReturnValue:
    """Create a new Customer with comprehensive validation"""
    try:
        data = await request.get_json()

        # Parse to Customer model for validation
        customer = Customer(**data)

        # Convert request to entity data
        entity_data = customer.model_dump(by_alias=True)

        # Save the entity
        response = await service.save(
            entity=entity_data,
            entity_class=Customer.ENTITY_NAME,
            entity_version=str(Customer.ENTITY_VERSION),
        )

        logger.info("Created Customer with ID: %s", response.metadata.id)

        # Return created entity directly (thin proxy)
        return _to_entity_dict(response.data), 201

    except ValueError as e:
        logger.warning("Validation error creating Customer: %s", str(e))
        return {"error": str(e), "code": "VALIDATION_ERROR"}, 400
    except Exception as e:
        logger.exception("Error creating Customer: %s", str(e))
        return {"error": str(e), "code": "INTERNAL_ERROR"}, 500


@customer_bp.route("/<entity_id>", methods=["GET"])
async def get_customer(entity_id: str) -> ResponseReturnValue:
    """Get Customer by ID with validation"""
    try:
        # Validate entity ID format
        if not entity_id or len(entity_id.strip()) == 0:
            return (
                jsonify({"error": "Entity ID is required", "code": "INVALID_ID"}),
                400,
            )

        response = await service.get_by_id(
            entity_id=entity_id,
            entity_class=Customer.ENTITY_NAME,
            entity_version=str(Customer.ENTITY_VERSION),
        )

        if not response:
            return {"error": "Customer not found", "code": "NOT_FOUND"}, 404

        # Thin proxy: return the entity directly
        return _to_entity_dict(response.data), 200

    except ValueError as e:
        logger.warning("Invalid entity ID %s: %s", entity_id, str(e))
        return {"error": str(e), "code": "INVALID_ID"}, 400
    except Exception as e:
        logger.exception("Error getting Customer %s: %s", entity_id, str(e))
        return {"error": str(e), "code": "INTERNAL_ERROR"}, 500


@customer_bp.route("", methods=["GET"])
async def list_customers() -> ResponseReturnValue:
    """List Customers with optional filtering"""
    try:
        # Get query parameters
        is_active = request.args.get("isActive")
        state = request.args.get("state")
        limit = int(request.args.get("limit", 100))
        offset = int(request.args.get("offset", 0))

        # Build search conditions based on query parameters
        search_conditions: Dict[str, str] = {}

        if is_active is not None:
            search_conditions["isActive"] = is_active.lower()

        if state:
            search_conditions["state"] = state

        # Get entities
        if search_conditions:
            # Build search condition request
            builder = SearchConditionRequest.builder()
            for field, value in search_conditions.items():
                builder.equals(field, value)
            condition = builder.build()

            entities = await service.search(
                entity_class=Customer.ENTITY_NAME,
                condition=condition,
                entity_version=str(Customer.ENTITY_VERSION),
            )
        else:
            entities = await service.find_all(
                entity_class=Customer.ENTITY_NAME,
                entity_version=str(Customer.ENTITY_VERSION),
            )

        # Thin proxy: return entities directly
        entity_list = [_to_entity_dict(r.data) for r in entities]

        # Apply pagination
        start = offset
        end = start + limit
        paginated_entities = entity_list[start:end]

        return jsonify({"entities": paginated_entities, "total": len(entity_list)}), 200

    except Exception as e:
        logger.exception("Error listing Customers: %s", str(e))
        return jsonify({"error": str(e)}), 500


@customer_bp.route("/<entity_id>", methods=["PUT"])
async def update_customer(entity_id: str) -> ResponseReturnValue:
    """Update Customer and optionally trigger workflow transition"""
    try:
        # Validate entity ID format
        if not entity_id or len(entity_id.strip()) == 0:
            return (
                jsonify({"error": "Entity ID is required", "code": "INVALID_ID"}),
                400,
            )

        data = await request.get_json()

        # Get transition from query parameters
        transition: Optional[str] = request.args.get("transition")

        # Parse to Customer model for validation
        customer = Customer(**data)

        # Convert request to entity data
        entity_data: Dict[str, Any] = customer.model_dump(by_alias=True)

        # Update the entity
        response = await service.update(
            entity_id=entity_id,
            entity=entity_data,
            entity_class=Customer.ENTITY_NAME,
            transition=transition,
            entity_version=str(Customer.ENTITY_VERSION),
        )

        logger.info("Updated Customer %s", entity_id)

        # Return updated entity directly (thin proxy)
        return jsonify(_to_entity_dict(response.data)), 200

    except ValueError as e:
        logger.warning("Validation error updating Customer %s: %s", entity_id, str(e))
        return jsonify({"error": str(e), "code": "VALIDATION_ERROR"}), 400
    except Exception as e:
        logger.exception("Error updating Customer %s: %s", entity_id, str(e))
        return jsonify({"error": str(e), "code": "INTERNAL_ERROR"}), 500


@customer_bp.route("/<entity_id>", methods=["DELETE"])
async def delete_customer(entity_id: str) -> ResponseReturnValue:
    """Delete Customer with validation"""
    try:
        # Validate entity ID format
        if not entity_id or len(entity_id.strip()) == 0:
            return (
                jsonify({"error": "Entity ID is required", "code": "INVALID_ID"}),
                400,
            )

        await service.delete_by_id(
            entity_id=entity_id,
            entity_class=Customer.ENTITY_NAME,
            entity_version=str(Customer.ENTITY_VERSION),
        )

        logger.info("Deleted Customer %s", entity_id)

        # Thin proxy: return success message
        return (
            jsonify(
                {
                    "success": True,
                    "message": "Customer deleted successfully",
                    "entity_id": entity_id,
                }
            ),
            200,
        )

    except ValueError as e:
        logger.warning("Invalid entity ID %s: %s", entity_id, str(e))
        return {"error": str(e), "code": "INVALID_ID"}, 400
    except Exception as e:
        logger.exception("Error deleting Customer %s: %s", entity_id, str(e))
        return {"error": str(e), "code": "INTERNAL_ERROR"}, 500


# ---- Additional Entity Service Endpoints ----------------------------------------


@customer_bp.route("/by-business-id/<business_id>", methods=["GET"])
async def get_by_business_id(business_id: str) -> ResponseReturnValue:
    """Get Customer by business ID (customer_id field by default)"""
    try:
        business_id_field = request.args.get("field", "customer_id")

        result = await service.find_by_business_id(
            entity_class=Customer.ENTITY_NAME,
            business_id=business_id,
            business_id_field=business_id_field,
            entity_version=str(Customer.ENTITY_VERSION),
        )

        if not result:
            return jsonify({"error": "Customer not found"}), 404

        # Thin proxy: return the entity directly
        return jsonify(_to_entity_dict(result.data)), 200

    except Exception as e:
        logger.exception(
            "Error getting Customer by business ID %s: %s", business_id, str(e)
        )
        return jsonify({"error": str(e)}), 500


@customer_bp.route("/<entity_id>/exists", methods=["GET"])
async def check_exists(entity_id: str) -> ResponseReturnValue:
    """Check if Customer exists by ID"""
    try:
        exists = await service.exists_by_id(
            entity_id=entity_id,
            entity_class=Customer.ENTITY_NAME,
            entity_version=str(Customer.ENTITY_VERSION),
        )

        return jsonify({"exists": exists, "entity_id": entity_id}), 200

    except Exception as e:
        logger.exception("Error checking Customer existence %s: %s", entity_id, str(e))
        return {"error": str(e)}, 500


@customer_bp.route("/count", methods=["GET"])
async def count_entities() -> ResponseReturnValue:
    """Count total number of Customers"""
    try:
        count = await service.count(
            entity_class=Customer.ENTITY_NAME,
            entity_version=str(Customer.ENTITY_VERSION),
        )

        return jsonify({"count": count}), 200

    except Exception as e:
        logger.exception("Error counting Customers: %s", str(e))
        return jsonify({"error": str(e)}), 500


@customer_bp.route("/search", methods=["POST"])
async def search_entities() -> ResponseReturnValue:
    """Search Customers using simple field-value search"""
    try:
        data = await request.get_json()

        if not data:
            return {"error": "Search conditions required", "code": "EMPTY_SEARCH"}, 400

        # Simple field-value search only
        builder = SearchConditionRequest.builder()
        for field, value in data.items():
            builder.equals(field, value)

        search_request = builder.build()
        results = await service.search(
            entity_class=Customer.ENTITY_NAME,
            condition=search_request,
            entity_version=str(Customer.ENTITY_VERSION),
        )

        # Thin proxy: return list of entities directly
        entities = [_to_entity_dict(r.data) for r in results]

        return {"entities": entities, "total": len(entities)}, 200

    except Exception as e:
        logger.exception("Error searching Customers: %s", str(e))
        return {"error": str(e)}, 500
