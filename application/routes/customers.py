"""
Customer Routes for Cyoda Client Application

Manages all Customer-related API endpoints including CRUD operations,
pagination, filtering, sorting, and workflow transitions as specified in requirements.
"""

from __future__ import annotations

import logging
import math
from datetime import datetime
from typing import Any, Dict, List, Optional

from quart import Blueprint, jsonify, request
from quart.typing import ResponseReturnValue
from quart_schema import (
    operation_id,
    tag,
    validate,
    validate_querystring,
)

from common.exception import is_not_found
from common.service.entity_service import SearchConditionRequest
from services.services import get_entity_service

# Import entity and models
from ..entity.customer.version_1.customer import Customer
from ..models.customer_models import (
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

# Module-level service proxy
class _ServiceProxy:
    def __getattr__(self, name: str) -> Any:
        return getattr(get_entity_service(), name)

service = _ServiceProxy()
logger = logging.getLogger(__name__)


# Helper to normalize entity data from service
def _to_entity_dict(data: Any) -> Dict[str, Any]:
    return data.model_dump(by_alias=True) if hasattr(data, "model_dump") else data


customers_bp = Blueprint("customers", __name__, url_prefix="/api/customers")


# ---- CRUD Operations --------------------------------------------------------

@customers_bp.route("", methods=["POST"])
@tag(["customers"])
@operation_id("create_customer")
@validate(
    request=Customer,
    responses={
        201: (CustomerResponse, None),
        400: (ValidationErrorResponse, None),
        409: (ErrorResponse, None),
        500: (ErrorResponse, None),
    },
)
async def create_customer(data: Customer) -> ResponseReturnValue:
    """Create a new Customer with comprehensive validation"""
    try:
        # Convert request to entity data
        entity_data = data.model_dump(by_alias=True)

        # Save the entity
        response = await service.save(
            entity=entity_data,
            entity_class=Customer.ENTITY_NAME,
            entity_version=str(Customer.ENTITY_VERSION),
        )

        logger.info("Created Customer with ID: %s", response.metadata.id)

        # Return created entity with Location header
        entity_dict = _to_entity_dict(response.data)
        headers = {"Location": f"/api/customers/{response.metadata.id}"}
        
        return entity_dict, 201, headers

    except ValueError as e:
        error_msg = str(e)
        if "already in use" in error_msg.lower() or "duplicate" in error_msg.lower():
            logger.warning("Duplicate email error creating Customer: %s", error_msg)
            return {"error": error_msg, "code": "DUPLICATE_EMAIL"}, 409
        else:
            logger.warning("Validation error creating Customer: %s", error_msg)
            return {"error": error_msg, "code": "VALIDATION_ERROR"}, 400
    except Exception as e:
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
    """Get Customer by ID"""
    try:
        if not customer_id or len(customer_id.strip()) == 0:
            return {"error": "Customer ID is required", "code": "INVALID_ID"}, 400

        response = await service.get_by_id(
            entity_id=customer_id,
            entity_class=Customer.ENTITY_NAME,
            entity_version=str(Customer.ENTITY_VERSION),
        )

        if not response:
            return {"error": "Customer not found", "code": "NOT_FOUND"}, 404

        return _to_entity_dict(response.data), 200

    except ValueError as e:
        logger.warning("Invalid customer ID %s: %s", customer_id, str(e))
        return {"error": str(e), "code": "INVALID_ID"}, 400
    except Exception as e:
        if is_not_found(e):
            return {"error": "Customer not found", "code": "NOT_FOUND"}, 404
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
async def list_customers(query_args: CustomerQueryParams) -> ResponseReturnValue:
    """List Customers with pagination, filtering, and sorting"""
    try:
        # Build search conditions
        search_conditions: Dict[str, str] = {}
        
        if query_args.name:
            search_conditions["name"] = query_args.name
        
        if query_args.email:
            search_conditions["email"] = query_args.email

        # Get entities
        if search_conditions:
            builder = SearchConditionRequest.builder()
            for field, value in search_conditions.items():
                # Use contains for partial matching on name and email
                builder.contains(field, value)
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

        # Convert to list of dicts
        entity_list = [_to_entity_dict(r.data) for r in entities]

        # Apply sorting
        if query_args.sort_by in ["name", "email", "created_at"]:
            reverse = query_args.order == "desc"
            entity_list.sort(
                key=lambda x: x.get(query_args.sort_by, ""),
                reverse=reverse
            )

        # Apply pagination
        total = len(entity_list)
        offset = (query_args.page - 1) * query_args.size
        paginated_entities = entity_list[offset:offset + query_args.size]
        total_pages = math.ceil(total / query_args.size) if total > 0 else 1

        return {
            "customers": paginated_entities,
            "total": total,
            "page": query_args.page,
            "size": query_args.size,
            "total_pages": total_pages
        }, 200

    except Exception as e:
        logger.exception("Error listing Customers: %s", str(e))
        return {"error": str(e), "code": "INTERNAL_ERROR"}, 500
