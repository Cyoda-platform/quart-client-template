"""
Response Models for Customer API endpoints.

Provides comprehensive response schemas for all API operations with proper
validation and documentation.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


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


# Customer Response Models
class CustomerResponse(BaseModel):
    """Response model for Customer operations."""

    id: str = Field(..., description="Customer UUID (server-generated)")
    entity_id: Optional[str] = Field(default=None, description="Entity ID")
    technical_id: Optional[str] = Field(
        default=None, description="Technical ID from Cyoda"
    )
    name: str = Field(..., description="Customer full name")
    email: str = Field(..., description="Customer email address")
    phone: Optional[str] = Field(default=None, description="Customer phone number")
    address: Optional[str] = Field(default=None, description="Customer address")
    state: str = Field(..., description="Current workflow state")
    created_at: Optional[str] = Field(
        default=None, alias="createdAt", description="Creation timestamp"
    )
    updated_at: Optional[str] = Field(
        default=None, alias="updatedAt", description="Last update timestamp"
    )
    version: Optional[str] = Field(default=None, description="Entity version")
    metadata: Optional[Dict[str, Any]] = Field(
        default=None, description="Entity metadata"
    )
    processed_data: Optional[Dict[str, Any]] = Field(
        default=None, alias="processedData", description="Processed data from workflows"
    )
    validation_result: Optional[Dict[str, Any]] = Field(
        default=None, alias="validationResult", description="Validation results"
    )


class CustomerListResponse(BaseModel):
    """Response model for Customer list operations."""

    customers: List[Dict[str, Any]] = Field(..., description="List of Customer objects")
    total: int = Field(..., description="Total number of customers")
    page: Optional[int] = Field(default=None, description="Current page number")
    page_size: Optional[int] = Field(default=None, description="Page size")
    total_pages: Optional[int] = Field(
        default=None, description="Total number of pages"
    )


class CustomerSearchResponse(BaseModel):
    """Response model for Customer search operations."""

    customers: List[Dict[str, Any]] = Field(..., description="Search results")
    total: int = Field(..., description="Total number of matching customers")
    query: Optional[Dict[str, Any]] = Field(
        default=None, description="Applied search query"
    )


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


class TransitionResponse(BaseModel):
    """Response model for workflow transition operations."""

    id: str = Field(..., description="Entity ID")
    message: str = Field(..., description="Transition result message")
    previous_state: Optional[str] = Field(
        default=None, alias="previousState", description="Previous workflow state"
    )
    new_state: str = Field(..., alias="newState", description="New workflow state")


class TransitionsResponse(BaseModel):
    """Response model for available transitions query."""

    entity_id: str = Field(..., description="Entity ID")
    available_transitions: List[str] = Field(
        ..., description="List of available transition names"
    )
    current_state: Optional[str] = Field(
        default=None, description="Current workflow state"
    )


class HealthResponse(BaseModel):
    """Response model for health check operations."""

    status: str = Field(..., description="Health status")
    timestamp: str = Field(..., description="Health check timestamp")
    version: Optional[str] = Field(default=None, description="Application version")


class StatusResponse(BaseModel):
    """Response model for status operations."""

    status: str = Field(..., description="Service status")
    message: Optional[str] = Field(default=None, description="Status message")
    details: Optional[Dict[str, Any]] = Field(
        default=None, description="Additional status details"
    )
