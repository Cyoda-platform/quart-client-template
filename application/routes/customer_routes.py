"""
Customer Routes for Cyoda Client Application

Manages all Customer-related API endpoints including CRUD operations
and workflow transitions following the thin proxy pattern.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from quart import Blueprint, request
from quart.typing import ResponseReturnValue

from application.entity.customer.version_1.customer import Customer

from common.service.entity_service import SearchConditionRequest
from services.services import get_entity_service

logger = logging.getLogger(__name__)


# Helper to normalize entity data from service (Pydantic model or dict)
def _to_entity_dict(data: Any) -> Dict[str, Any]:
    return data.model_dump(by_alias=True) if hasattr(data, "model_dump") else data


customer_bp = Blueprint("customers", __name__, url_prefix="/api/customers")


@customer_bp.route("", methods=["POST"])
async def create_customer() -> ResponseReturnValue:
    """Create a new Customer"""
    try:
        data = await request.get_json()

        # Parse to Customer model for validation
        customer = Customer(**data)

        # Convert to dict for EntityService
        entity_data = customer.model_dump(by_alias=True)

        # Save the entity
        response = await get_entity_service().save(
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
    """Get Customer by ID"""
    try:
        # Validate entity ID format
        if not entity_id or len(entity_id.strip()) == 0:
            return {"error": "Entity ID is required", "code": "INVALID_ID"}, 400

        response = await get_entity_service().get_by_id(
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
    """List all Customers with optional filtering"""
    try:
        # Get query parameters
        customer_id = request.args.get("customer_id")
        email = request.args.get("email")
        state = request.args.get("state")

        # Build search conditions
        search_conditions: Dict[str, str] = {}
        if customer_id:
            search_conditions["customer_id"] = customer_id
        if email:
            search_conditions["email"] = email
        if state:
            search_conditions["state"] = state

        # Get entities
        if search_conditions:
            # Build search condition request
            builder = SearchConditionRequest.builder()
            for field, value in search_conditions.items():
                builder.equals(field, value)
            condition = builder.build()

            entities = await get_entity_service().search(
                entity_class=Customer.ENTITY_NAME,
                condition=condition,
                entity_version=str(Customer.ENTITY_VERSION),
            )
        else:
            entities = await get_entity_service().find_all(
                entity_class=Customer.ENTITY_NAME,
                entity_version=str(Customer.ENTITY_VERSION),
            )

        # Thin proxy: return entities directly
        entity_list = [_to_entity_dict(r.data) for r in entities]

        return {"customers": entity_list, "total": len(entity_list)}, 200

    except Exception as e:
        logger.exception("Error listing Customers: %s", str(e))
        return {"error": str(e)}, 500


@customer_bp.route("/<entity_id>", methods=["PUT"])
async def update_customer(entity_id: str) -> ResponseReturnValue:
    """Update Customer and optionally trigger workflow transition"""
    try:
        # Validate entity ID format
        if not entity_id or len(entity_id.strip()) == 0:
            return {"error": "Entity ID is required", "code": "INVALID_ID"}, 400

        data = await request.get_json()

        # Get transition from query parameters
        transition: Optional[str] = request.args.get("transition")

        # Parse to Customer model for validation
        customer = Customer(**data)

        # Convert to dict for EntityService
        entity_data = customer.model_dump(by_alias=True)

        # Update the entity
        response = await get_entity_service().update(
            entity_id=entity_id,
            entity=entity_data,
            entity_class=Customer.ENTITY_NAME,
            transition=transition,
            entity_version=str(Customer.ENTITY_VERSION),
        )

        logger.info("Updated Customer %s", entity_id)

        # Return updated entity directly (thin proxy)
        return _to_entity_dict(response.data), 200

    except ValueError as e:
        logger.warning("Validation error updating Customer %s: %s", entity_id, str(e))
        return {"error": str(e), "code": "VALIDATION_ERROR"}, 400
    except Exception as e:
        logger.exception("Error updating Customer %s: %s", entity_id, str(e))
        return {"error": str(e), "code": "INTERNAL_ERROR"}, 500


@customer_bp.route("/<entity_id>", methods=["DELETE"])
async def delete_customer(entity_id: str) -> ResponseReturnValue:
    """Delete Customer"""
    try:
        # Validate entity ID format
        if not entity_id or len(entity_id.strip()) == 0:
            return {"error": "Entity ID is required", "code": "INVALID_ID"}, 400

        await get_entity_service().delete_by_id(
            entity_id=entity_id,
            entity_class=Customer.ENTITY_NAME,
            entity_version=str(Customer.ENTITY_VERSION),
        )

        logger.info("Deleted Customer %s", entity_id)

        # Thin proxy: return success message
        return {
            "success": True,
            "message": "Customer deleted successfully",
            "entity_id": entity_id,
        }, 200

    except ValueError as e:
        logger.warning("Invalid entity ID %s: %s", entity_id, str(e))
        return {"error": str(e), "code": "INVALID_ID"}, 400
    except Exception as e:
        logger.exception("Error deleting Customer %s: %s", entity_id, str(e))
        return {"error": str(e), "code": "INTERNAL_ERROR"}, 500


@customer_bp.route("/by-customer-id/<customer_id>", methods=["GET"])
async def get_by_customer_id(customer_id: str) -> ResponseReturnValue:
    """Get Customer by business ID (customer_id field)"""
    try:
        result = await get_entity_service().find_by_business_id(
            entity_class=Customer.ENTITY_NAME,
            business_id=customer_id,
            business_id_field="customer_id",
            entity_version=str(Customer.ENTITY_VERSION),
        )

        if not result:
            return {"error": "Customer not found", "code": "NOT_FOUND"}, 404

        # Thin proxy: return the entity directly
        return _to_entity_dict(result.data), 200

    except Exception as e:
        logger.exception(
            "Error getting Customer by customer ID %s: %s", customer_id, str(e)
        )
        return {"error": str(e)}, 500


@customer_bp.route("/<entity_id>/transitions", methods=["POST"])
async def trigger_transition(entity_id: str) -> ResponseReturnValue:
    """Trigger a specific workflow transition"""
    try:
        data = await request.get_json()
        transition_name = data.get("transition_name")

        if not transition_name:
            return {
                "error": "transition_name is required",
                "code": "MISSING_PARAMETER",
            }, 400

        # Get current entity state
        current_entity = await get_entity_service().get_by_id(
            entity_id=entity_id,
            entity_class=Customer.ENTITY_NAME,
            entity_version=str(Customer.ENTITY_VERSION),
        )

        if not current_entity:
            return {"error": "Customer not found", "code": "NOT_FOUND"}, 404

        previous_state = current_entity.metadata.state

        # Execute the transition
        response = await get_entity_service().execute_transition(
            entity_id=entity_id,
            transition=transition_name,
            entity_class=Customer.ENTITY_NAME,
            entity_version=str(Customer.ENTITY_VERSION),
        )

        logger.info(
            "Executed transition '%s' on Customer %s", transition_name, entity_id
        )

        return {
            "id": response.metadata.id,
            "message": "Transition executed successfully",
            "previousState": previous_state,
            "newState": response.metadata.state,
        }, 200

    except Exception as e:
        logger.exception(
            "Error executing transition on Customer %s: %s", entity_id, str(e)
        )
        return {"error": str(e)}, 500
