"""
Customer Models for Customer API endpoints.

Provides comprehensive request and response schemas for all Customer API operations
with proper validation and documentation.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, EmailStr, Field


# Base Response Models
class ErrorResponse(BaseModel):
    """Standard error response model."""

    error: str = Field(..., description="Error message")
    details: Optional[Dict[str, Any]] = Field(
        default=None, description="Additional error details"
    )
    code: Optional[str] = Field(default=None, description="Error code")
    timestamp: Optional[str] = Field(default=None, description="Error timestamp")


class ValidationErrorResponse(BaseModel):
    """Validation error response model."""

    error: str = Field(..., description="Validation error message")
    field_errors: Optional[Dict[str, List[str]]] = Field(
        default=None, description="Field-specific validation errors"
    )
    code: str = Field(default="VALIDATION_ERROR", description="Error code")


class SuccessResponse(BaseModel):
    """Standard success response model."""

    message: str = Field(..., description="Success message")
    data: Optional[Dict[str, Any]] = Field(default=None, description="Response data")


class DeleteResponse(BaseModel):
    """Response model for delete operations."""

    success: bool = Field(..., description="Whether the operation was successful")
    message: str = Field(..., description="Success message")
    entity_id: str = Field(..., description="ID of the deleted entity")


class ExistsResponse(BaseModel):
    """Response model for existence check operations."""

    exists: bool = Field(..., description="Whether the entity exists")
    entity_id: str = Field(..., description="Entity ID that was checked")


class CountResponse(BaseModel):
    """Response model for count operations."""

    count: int = Field(..., description="Total count of entities")


# Customer Response Models
class CustomerResponse(BaseModel):
    """Response model for Customer operations."""

    entity_id: str = Field(..., description="Entity ID")
    technical_id: Optional[str] = Field(
        default=None, description="Technical ID from Cyoda"
    )
    name: str = Field(..., description="Customer name")
    email: EmailStr = Field(..., description="Customer email")
    phone: str = Field(..., description="Customer phone number")
    address_line1: str = Field(
        ..., alias="addressLine1", description="Primary address line"
    )
    address_line2: Optional[str] = Field(
        default=None, alias="addressLine2", description="Secondary address line"
    )
    city: str = Field(..., description="City")
    state: Optional[str] = Field(default=None, description="State or province")
    postal_code: str = Field(..., alias="postalCode", description="Postal code")
    country: str = Field(..., description="Country")
    is_active: bool = Field(..., alias="isActive", description="Active status")
    customer_type: str = Field(..., alias="customerType", description="Customer type")
    workflow_state: str = Field(..., description="Current workflow state")
    created_at: Optional[str] = Field(
        default=None, alias="createdAt", description="Creation timestamp"
    )
    updated_at: Optional[str] = Field(
        default=None, alias="updatedAt", description="Last update timestamp"
    )
    version: str = Field(..., description="Entity version")
    metadata: Optional[Dict[str, Any]] = Field(
        default=None, description="Entity metadata"
    )
    validation_result: Optional[Dict[str, Any]] = Field(
        default=None, alias="validationResult", description="Validation results"
    )
    enriched_data: Optional[Dict[str, Any]] = Field(
        default=None, alias="enrichedData", description="Enriched data from processing"
    )


class CustomerListResponse(BaseModel):
    """Response model for Customer list operations."""

    customers: List[Dict[str, Any]] = Field(..., description="List of Customer objects")
    total: int = Field(..., description="Total number of customers")
    limit: Optional[int] = Field(default=None, description="Applied limit")
    offset: Optional[int] = Field(default=None, description="Applied offset")


class CustomerSearchResponse(BaseModel):
    """Response model for Customer search operations."""

    customers: List[Dict[str, Any]] = Field(..., description="Search results")
    total: int = Field(..., description="Total number of matching customers")
    query: Optional[Dict[str, Any]] = Field(
        default=None, description="Applied search query"
    )


# Request Models
class CustomerQueryParams(BaseModel):
    """Query parameters for Customer list operations."""

    customer_type: Optional[str] = Field(
        default=None, alias="customerType", description="Filter by customer type"
    )
    is_active: Optional[bool] = Field(
        default=None, alias="isActive", description="Filter by active status"
    )
    state: Optional[str] = Field(default=None, description="Filter by workflow state")
    city: Optional[str] = Field(default=None, description="Filter by city")
    country: Optional[str] = Field(default=None, description="Filter by country")
    limit: int = Field(default=50, description="Maximum number of results")
    offset: int = Field(default=0, description="Number of results to skip")


class CustomerUpdateQueryParams(BaseModel):
    """Query parameters for Customer update operations."""

    transition: Optional[str] = Field(
        default=None, description="Workflow transition to trigger"
    )


class SearchRequest(BaseModel):
    """Request model for search operations."""

    name: Optional[str] = Field(default=None, description="Search by name")
    email: Optional[str] = Field(default=None, description="Search by email")
    customer_type: Optional[str] = Field(
        default=None, alias="customerType", description="Search by customer type"
    )
    city: Optional[str] = Field(default=None, description="Search by city")
    country: Optional[str] = Field(default=None, description="Search by country")
    is_active: Optional[bool] = Field(
        default=None, alias="isActive", description="Search by active status"
    )


class TransitionRequest(BaseModel):
    """Request model for workflow transition operations."""

    transition_name: str = Field(..., description="Name of the transition to execute")


class TransitionResponse(BaseModel):
    """Response model for workflow transition operations."""

    entity_id: str = Field(..., description="Entity ID")
    message: str = Field(..., description="Transition result message")
    previous_state: str = Field(..., description="Previous workflow state")
    new_state: str = Field(..., description="New workflow state")


class TransitionsResponse(BaseModel):
    """Response model for available transitions query."""

    entity_id: str = Field(..., description="Entity ID")
    available_transitions: List[str] = Field(
        ..., description="List of available transition names"
    )
    current_state: Optional[str] = Field(
        default=None, description="Current workflow state"
    )
