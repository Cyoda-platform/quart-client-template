"""
Customer Routes for Cyoda Client Application

Manages all Customer-related API endpoints including CRUD operations
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


customers_bp = Blueprint(
    "customers", __name__, url_prefix="/api/customers"
)


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

        return jsonify({
            "customers": paginated_entities, 
            "total": total,
            "page": query_args.page,
            "page_size": query_args.page_size,
            "total_pages": total_pages
        }), 200

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
        logger.warning(
            "Validation error updating Customer %s: %s", customer_id, str(e)
        )
        return jsonify({"error": str(e), "code": "VALIDATION_ERROR"}), 400
    except Exception as e:  # pragma: no cover
        logger.exception("Error updating Customer %s: %s", customer_id, str(e))
        return jsonify({"error": str(e), "code": "INTERNAL_ERROR"}), 500
