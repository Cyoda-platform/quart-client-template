"""
Customer API Models for request/response handling
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class CustomerQueryParams(BaseModel):
    """Query parameters for listing customers"""

    page: int = Field(default=1, ge=1, description="Page number (1-based)")
    size: int = Field(default=20, ge=1, le=100, description="Page size (max 100)")
    name: Optional[str] = Field(
        default=None, description="Filter by name (partial match)"
    )
    email: Optional[str] = Field(
        default=None, description="Filter by email (partial match)"
    )
    sort_by: Optional[str] = Field(
        default="created_at", description="Sort field: name, email, created_at"
    )
    order: Optional[str] = Field(default="desc", description="Sort order: asc or desc")


class CustomerUpdateQueryParams(BaseModel):
    """Query parameters for updating customers"""

    transition: Optional[str] = Field(
        default=None, description="Workflow transition to trigger"
    )


class CustomerResponse(BaseModel):
    """Response model for single customer"""

    id: str = Field(..., description="Customer technical ID")
    name: str = Field(..., description="Customer name")
    email: str = Field(..., description="Customer email")
    phone: Optional[str] = Field(default=None, description="Customer phone")
    address: Optional[Dict[str, Any]] = Field(
        default=None, description="Customer address"
    )
    state: Optional[str] = Field(default=None, description="Workflow state")
    created_at: Optional[str] = Field(default=None, description="Creation timestamp")
    updated_at: Optional[str] = Field(default=None, description="Update timestamp")


class CustomerListResponse(BaseModel):
    """Response model for customer list"""

    customers: List[CustomerResponse] = Field(..., description="List of customers")
    total: int = Field(..., description="Total number of customers")
    page: int = Field(..., description="Current page number")
    size: int = Field(..., description="Page size")
    total_pages: int = Field(..., description="Total number of pages")


class CustomerSearchResponse(BaseModel):
    """Response model for customer search"""

    customers: List[CustomerResponse] = Field(
        ..., description="List of matching customers"
    )
    total: int = Field(..., description="Total number of matches")


class ErrorResponse(BaseModel):
    """Error response model"""

    error: str = Field(..., description="Error message")
    code: Optional[str] = Field(default=None, description="Error code")
    details: Optional[Dict[str, Any]] = Field(
        default=None, description="Additional error details"
    )


class ValidationErrorResponse(BaseModel):
    """Validation error response model"""

    error: str = Field(..., description="Validation error message")
    code: str = Field(default="VALIDATION_ERROR", description="Error code")
    field_errors: Optional[Dict[str, List[str]]] = Field(
        default=None, description="Field-specific errors"
    )


class DeleteResponse(BaseModel):
    """Response model for delete operations"""

    success: bool = Field(..., description="Whether the operation was successful")
    message: str = Field(..., description="Success message")
    entity_id: str = Field(..., description="ID of the deleted entity")


class ExistsResponse(BaseModel):
    """Response model for existence checks"""

    exists: bool = Field(..., description="Whether the entity exists")
    entity_id: str = Field(..., description="Entity ID that was checked")


class CountResponse(BaseModel):
    """Response model for count operations"""

    count: int = Field(..., description="Number of entities")


class TransitionRequest(BaseModel):
    """Request model for workflow transitions"""

    transition_name: str = Field(..., description="Name of the transition to execute")


class TransitionResponse(BaseModel):
    """Response model for workflow transitions"""

    id: str = Field(..., description="Entity ID")
    message: str = Field(..., description="Success message")
    previous_state: Optional[str] = Field(
        default=None, description="Previous workflow state"
    )
    new_state: Optional[str] = Field(default=None, description="New workflow state")


class TransitionsResponse(BaseModel):
    """Response model for available transitions"""

    entity_id: str = Field(..., description="Entity ID")
    available_transitions: List[str] = Field(
        ..., description="List of available transitions"
    )
    current_state: Optional[str] = Field(
        default=None, description="Current workflow state"
    )


class SearchRequest(BaseModel):
    """Request model for search operations"""

    name: Optional[str] = Field(default=None, description="Search by name")
    email: Optional[str] = Field(default=None, description="Search by email")
    phone: Optional[str] = Field(default=None, description="Search by phone")
    state: Optional[str] = Field(default=None, description="Search by workflow state")
