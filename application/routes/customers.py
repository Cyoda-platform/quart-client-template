"""
Customer Routes for Cyoda Client Application

Manages all Customer-related API endpoints including CRUD operations
and workflow transitions as specified in functional requirements.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from quart import Blueprint, jsonify, request
from quart.typing import ResponseReturnValue
from quart_schema import (
    operation_id,
    tag,
    validate,
    validate_querystring,
)


from common.service.entity_service import (
    SearchConditionRequest,
)
from services.services import get_entity_service

# Imported for entity constants / typing
from ..entity.customer.version_1.customer import Customer
from ..models import (
    CountResponse,
    CustomerListResponse,
    CustomerQueryParams,
    CustomerResponse,
    CustomerSearchResponse,
    CustomerUpdateQueryParams,
    DeleteResponse,
    ErrorResponse,
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
    return data.model_dump(by_alias=True) if hasattr(data, "model_dump") else data


customers_bp = Blueprint("customers", __name__, url_prefix="/api/customers")


# ---- Routes -----------------------------------------------------------------


@customers_bp.route("", methods=["POST"])
@tag(["customers"])
@operation_id("create_customer")
@validate(
    request=Customer,
    responses={
        201: (CustomerResponse, None),
        400: (ValidationErrorResponse, None),
        500: (ErrorResponse, None),
    },
)
async def create_customer(
    data: Customer,
) -> ResponseReturnValue:
    """Create a new Customer with comprehensive validation"""
    try:
        # Convert request to entity data (same pattern as other entities)
        entity_data = data.model_dump(by_alias=True)

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
    except Exception as e:  # pragma: no cover - keep robust error handling
        logger.exception("Error creating Customer: %s", str(e))
        return {"error": str(e), "code": "INTERNAL_ERROR"}, 500


@customers_bp.route("/<customer_id>", methods=["GET"])
@tag(["customers"])
@operation_id("get_customer")
@validate(
    responses={
        200: (CustomerResponse, None),
        404: (ErrorResponse, None),
        400: (ErrorResponse, None),
        500: (ErrorResponse, None),
    }
)
async def get_customer(customer_id: str) -> ResponseReturnValue:
    """Get Customer by ID with validation"""
    try:
        # Validate customer ID format
        if not customer_id or len(customer_id.strip()) == 0:
            return (
                jsonify({"error": "Customer ID is required", "code": "INVALID_ID"}),
                400,
            )

        response = await service.get_by_id(
            entity_id=customer_id,
            entity_class=Customer.ENTITY_NAME,
            entity_version=str(Customer.ENTITY_VERSION),
        )

        if not response:
            return {"error": "Customer not found", "code": "NOT_FOUND"}, 404

        # Thin proxy: return the entity directly
        return _to_entity_dict(response.data), 200

    except ValueError as e:
        logger.warning("Invalid customer ID %s: %s", customer_id, str(e))
        return {"error": str(e), "code": "INVALID_ID"}, 400
    except Exception as e:  # pragma: no cover
        logger.exception("Error getting Customer %s: %s", customer_id, str(e))
        return {"error": str(e), "code": "INTERNAL_ERROR"}, 500


@customers_bp.route("", methods=["GET"])
@validate_querystring(CustomerQueryParams)
@tag(["customers"])
@operation_id("list_customers")
@validate(
    responses={
        200: (CustomerListResponse, None),
        400: (ValidationErrorResponse, None),
        500: (ErrorResponse, None),
    }
)
async def list_customers(
    query_args: CustomerQueryParams,
) -> ResponseReturnValue:
    """List Customers with optional filtering and pagination"""
    try:
        # Build search conditions based on query parameters
        search_conditions: Dict[str, str] = {}

        if query_args.name:
            search_conditions["name"] = query_args.name

        if query_args.email:
            search_conditions["email"] = query_args.email

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
        start = query_args.offset
        end = start + query_args.limit
        paginated_entities = entity_list[start:end]

        # Calculate pagination metadata
        total = len(entity_list)
        total_pages = (total + query_args.page_size - 1) // query_args.page_size

        return (
            jsonify(
                {
                    "customers": paginated_entities,
                    "total": total,
                    "page": query_args.page,
                    "page_size": query_args.page_size,
                    "total_pages": total_pages,
                }
            ),
            200,
        )

    except Exception as e:  # pragma: no cover
        logger.exception("Error listing Customers: %s", str(e))
        return jsonify({"error": str(e)}), 500


@customers_bp.route("/<customer_id>", methods=["PUT"])
@validate_querystring(CustomerUpdateQueryParams)
@tag(["customers"])
@operation_id("update_customer")
@validate(
    request=Customer,
    responses={
        200: (CustomerResponse, None),
        404: (ErrorResponse, None),
        400: (ValidationErrorResponse, None),
        500: (ErrorResponse, None),
    },
)
async def update_customer(
    customer_id: str, data: Customer, query_args: CustomerUpdateQueryParams
) -> ResponseReturnValue:
    """Update Customer (full update) and optionally trigger workflow transition with validation"""
    try:
        # Validate customer ID format
        if not customer_id or len(customer_id.strip()) == 0:
            return (
                jsonify({"error": "Customer ID is required", "code": "INVALID_ID"}),
                400,
            )

        # Get transition from query parameters
        transition: Optional[str] = query_args.transition

        # Convert request to entity data (entity model as-is)
        entity_data: Dict[str, Any] = data.model_dump(by_alias=True)

        # Update the entity
        response = await service.update(
            entity_id=customer_id,
            entity=entity_data,
            entity_class=Customer.ENTITY_NAME,
            transition=transition,
            entity_version=str(Customer.ENTITY_VERSION),
        )

        logger.info("Updated Customer %s", customer_id)

        # Return updated entity directly (thin proxy)
        return jsonify(_to_entity_dict(response.data)), 200

    except ValueError as e:
        logger.warning("Validation error updating Customer %s: %s", customer_id, str(e))
        return jsonify({"error": str(e), "code": "VALIDATION_ERROR"}), 400
    except Exception as e:  # pragma: no cover
        logger.exception("Error updating Customer %s: %s", customer_id, str(e))
        return jsonify({"error": str(e), "code": "INTERNAL_ERROR"}), 500


@customers_bp.route("/<customer_id>", methods=["PATCH"])
@validate_querystring(CustomerUpdateQueryParams)
@tag(["customers"])
@operation_id("patch_customer")
@validate(
    responses={
        200: (CustomerResponse, None),
        404: (ErrorResponse, None),
        400: (ValidationErrorResponse, None),
        500: (ErrorResponse, None),
    },
)
async def patch_customer(
    customer_id: str, query_args: CustomerUpdateQueryParams
) -> ResponseReturnValue:
    """Update Customer (partial update) and optionally trigger workflow transition"""
    try:
        # Validate customer ID format
        if not customer_id or len(customer_id.strip()) == 0:
            return (
                jsonify({"error": "Customer ID is required", "code": "INVALID_ID"}),
                400,
            )

        # Get current customer
        current_response = await service.get_by_id(
            entity_id=customer_id,
            entity_class=Customer.ENTITY_NAME,
            entity_version=str(Customer.ENTITY_VERSION),
        )

        if not current_response:
            return {"error": "Customer not found", "code": "NOT_FOUND"}, 404

        # Get JSON data from request
        patch_data = await request.get_json()
        if not patch_data:
            return {"error": "Request body is required", "code": "MISSING_BODY"}, 400

        # Get current entity data
        current_data = _to_entity_dict(current_response.data)

        # Apply patch data (only update provided fields)
        for key, value in patch_data.items():
            if key in ["name", "email", "phone", "address"]:
                current_data[key] = value

        # Validate the updated data by creating a Customer instance
        try:
            updated_customer = Customer(**current_data)
            entity_data = updated_customer.model_dump(by_alias=True)
        except Exception as e:
            return {
                "error": f"Validation error: {str(e)}",
                "code": "VALIDATION_ERROR",
            }, 400

        # Get transition from query parameters
        transition: Optional[str] = query_args.transition

        # Update the entity
        response = await service.update(
            entity_id=customer_id,
            entity=entity_data,
            entity_class=Customer.ENTITY_NAME,
            transition=transition,
            entity_version=str(Customer.ENTITY_VERSION),
        )

        logger.info("Patched Customer %s", customer_id)

        # Return updated entity directly (thin proxy)
        return jsonify(_to_entity_dict(response.data)), 200

    except ValueError as e:
        logger.warning("Validation error patching Customer %s: %s", customer_id, str(e))
        return jsonify({"error": str(e), "code": "VALIDATION_ERROR"}), 400
    except Exception as e:  # pragma: no cover
        logger.exception("Error patching Customer %s: %s", customer_id, str(e))
        return jsonify({"error": str(e), "code": "INTERNAL_ERROR"}), 500


@customers_bp.route("/<customer_id>", methods=["DELETE"])
@tag(["customers"])
@operation_id("delete_customer")
@validate(
    responses={
        200: (DeleteResponse, None),
        404: (ErrorResponse, None),
        400: (ErrorResponse, None),
        500: (ErrorResponse, None),
    }
)
async def delete_customer(customer_id: str) -> ResponseReturnValue:
    """Delete Customer with validation"""
    try:
        # Validate customer ID format
        if not customer_id or len(customer_id.strip()) == 0:
            return (
                jsonify({"error": "Customer ID is required", "code": "INVALID_ID"}),
                400,
            )

        await service.delete_by_id(
            entity_id=customer_id,
            entity_class=Customer.ENTITY_NAME,
            entity_version=str(Customer.ENTITY_VERSION),
        )

        logger.info("Deleted Customer %s", customer_id)

        # Thin proxy: return success message
        response = DeleteResponse(
            success=True,
            message="Customer deleted successfully",
            entity_id=customer_id,
        )
        return response.model_dump(), 200

    except ValueError as e:
        logger.warning("Invalid customer ID %s: %s", customer_id, str(e))
        return {"error": str(e), "code": "INVALID_ID"}, 400
    except Exception as e:  # pragma: no cover
        logger.exception("Error deleting Customer %s: %s", customer_id, str(e))
        return {"error": str(e), "code": "INTERNAL_ERROR"}, 500


# ---- Additional Entity Service Endpoints ----------------------------------------


@customers_bp.route("/by-business-id/<business_id>", methods=["GET"])
@tag(["customers"])
@operation_id("get_customer_by_business_id")
@validate(
    responses={
        200: (CustomerResponse, None),
        404: (ErrorResponse, None),
        500: (ErrorResponse, None),
    }
)
async def get_by_business_id(business_id: str) -> ResponseReturnValue:
    """Get Customer by business ID (email field by default)"""
    try:
        business_id_field = request.args.get("field", "email")  # Default to email field

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


@customers_bp.route("/<customer_id>/exists", methods=["GET"])
@tag(["customers"])
@operation_id("check_customer_exists")
@validate(responses={200: (ExistsResponse, None), 500: (ErrorResponse, None)})
async def check_exists(customer_id: str) -> ResponseReturnValue:
    """Check if Customer exists by ID"""
    try:
        exists = await service.exists_by_id(
            entity_id=customer_id,
            entity_class=Customer.ENTITY_NAME,
            entity_version=str(Customer.ENTITY_VERSION),
        )

        response = ExistsResponse(exists=exists, entity_id=customer_id)
        return response.model_dump(), 200

    except Exception as e:
        logger.exception(
            "Error checking Customer existence %s: %s", customer_id, str(e)
        )
        return {"error": str(e)}, 500


@customers_bp.route("/count", methods=["GET"])
@tag(["customers"])
@operation_id("count_customers")
@validate(responses={200: (CountResponse, None), 500: (ErrorResponse, None)})
async def count_entities() -> ResponseReturnValue:
    """Count total number of Customers"""
    try:
        service = get_entity_service()

        count = await service.count(
            entity_class=Customer.ENTITY_NAME,
            entity_version=str(Customer.ENTITY_VERSION),
        )

        response = CountResponse(count=count)
        return jsonify(response.model_dump()), 200

    except Exception as e:
        logger.exception("Error counting Customers: %s", str(e))
        return jsonify({"error": str(e)}), 500


@customers_bp.route("/<customer_id>/transitions", methods=["GET"])
@tag(["customers"])
@operation_id("get_customer_transitions")
@validate(
    responses={
        200: (TransitionsResponse, None),
        404: (ErrorResponse, None),
        500: (ErrorResponse, None),
    }
)
async def get_available_transitions(customer_id: str) -> ResponseReturnValue:
    """Get available workflow transitions for Customer"""
    try:
        transitions = await service.get_transitions(
            entity_id=customer_id,
            entity_class=Customer.ENTITY_NAME,
            entity_version=str(Customer.ENTITY_VERSION),
        )

        response = TransitionsResponse(
            entity_id=customer_id,
            available_transitions=transitions,
            current_state=None,  # Could be enhanced to get current state
        )
        return jsonify(response.model_dump()), 200

    except Exception as e:
        logger.exception(
            "Error getting transitions for Customer %s: %s", customer_id, str(e)
        )
        return jsonify({"error": str(e)}), 500


# ---- Search Endpoints -----------------------------------------------------------


@customers_bp.route("/search", methods=["POST"])
@tag(["customers"])
@operation_id("search_customers")
@validate(
    request=SearchRequest,
    responses={
        200: (CustomerSearchResponse, None),
        400: (ValidationErrorResponse, None),
        500: (ErrorResponse, None),
    },
)
async def search_entities(data: SearchRequest) -> ResponseReturnValue:
    """Search Customers using simple field-value search with validation"""
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
            entity_class=Customer.ENTITY_NAME,
            condition=search_request,
            entity_version=str(Customer.ENTITY_VERSION),
        )

        # Thin proxy: return list of entities directly
        entities = [_to_entity_dict(r.data) for r in results]

        return {"customers": entities, "total": len(entities)}, 200

    except Exception as e:
        logger.exception("Error searching Customers: %s", str(e))
        return {"error": str(e)}, 500


@customers_bp.route("/find-all", methods=["GET"])
@tag(["customers"])
@operation_id("find_all_customers")
@validate(responses={200: (CustomerListResponse, None), 500: (ErrorResponse, None)})
async def find_all_entities() -> ResponseReturnValue:
    """Find all Customers without filtering"""
    try:
        results = await service.find_all(
            entity_class=Customer.ENTITY_NAME,
            entity_version=str(Customer.ENTITY_VERSION),
        )

        entities = [_to_entity_dict(r.data) for r in results]
        return {"customers": entities, "total": len(entities)}, 200

    except Exception as e:
        logger.exception("Error finding all Customers: %s", str(e))
        return {"error": str(e)}, 500


@customers_bp.route("/<customer_id>/transitions", methods=["POST"])
@tag(["customers"])
@operation_id("trigger_customer_transition")
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
    customer_id: str, data: TransitionRequest
) -> ResponseReturnValue:
    """Trigger a specific workflow transition with validation"""
    try:
        # Get current entity state
        current_entity = await service.get_by_id(
            entity_id=customer_id,
            entity_class=Customer.ENTITY_NAME,
            entity_version=str(Customer.ENTITY_VERSION),
        )

        if not current_entity:
            return jsonify({"error": "Customer not found"}), 404

        previous_state = current_entity.metadata.state

        # Execute the transition
        response = await service.execute_transition(
            entity_id=customer_id,
            transition=data.transition_name,
            entity_class=Customer.ENTITY_NAME,
            entity_version=str(Customer.ENTITY_VERSION),
        )

        logger.info(
            "Executed transition '%s' on Customer %s",
            data.transition_name,
            customer_id,
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
            "Error executing transition on Customer %s: %s", customer_id, str(e)
        )
        return jsonify({"error": str(e)}), 500
