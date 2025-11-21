"""
Models package for Customer Application.

Provides request and response models for comprehensive API validation.
"""

from .request_models import (
    CustomerQueryParams,
    CustomerUpdateQueryParams,
    ErrorResponse,
    SearchRequest,
    SuccessResponse,
    TransitionRequest,
)
from .response_models import (
    CountResponse,
    CustomerListResponse,
    CustomerResponse,
    CustomerSearchResponse,
    DeleteResponse,
    ExistsResponse,
    TransitionResponse,
    TransitionsResponse,
    ValidationErrorResponse,
)

__all__ = [
    # Request models
    "CustomerQueryParams",
    "CustomerUpdateQueryParams",
    "ErrorResponse",
    "SearchRequest",
    "SuccessResponse",
    "TransitionRequest",
    # Response models
    "CountResponse",
    "CustomerListResponse",
    "CustomerResponse",
    "CustomerSearchResponse",
    "DeleteResponse",
    "ExistsResponse",
    "TransitionResponse",
    "TransitionsResponse",
    "ValidationErrorResponse",
]
