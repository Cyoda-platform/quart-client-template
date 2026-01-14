"""
Response Models for Application API endpoints.

Provides comprehensive response schemas for all API operations with proper
validation and documentation.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    """Standard error response model."""

    error: str = Field(..., description="Error message")
    details: Optional[Dict[str, Any]] = Field(
        default=None, description="Additional error details"
    )
    code: Optional[str] = Field(default=None, description="Error code")
    timestamp: Optional[str] = Field(default=None, description="Error timestamp")


class SuccessResponse(BaseModel):
    """Standard success response model."""

    message: str = Field(..., description="Success message")
    data: Optional[Dict[str, Any]] = Field(default=None, description="Response data")


class EntityResponse(BaseModel):
    """Response model for single entity operations."""

    entity_id: str = Field(..., description="Entity ID")
    technical_id: Optional[str] = Field(
        default=None, description="Technical ID from Cyoda"
    )
    state: Optional[str] = Field(default=None, description="Current workflow state")
    created_at: Optional[str] = Field(default=None, description="Creation timestamp")
    updated_at: Optional[str] = Field(default=None, description="Last update timestamp")
    data: Optional[Dict[str, Any]] = Field(default=None, description="Entity data")


class EntityListResponse(BaseModel):
    """Response model for entity list operations."""

    entities: list[Dict[str, Any]] = Field(..., description="List of entities")
    total: int = Field(..., description="Total number of entities")


class TransitionResponse(BaseModel):
    """Response model for state transition operations."""

    entity_id: str = Field(..., description="Entity ID")
    previous_state: str = Field(..., description="Previous workflow state")
    new_state: str = Field(..., description="New workflow state")
    transition_name: str = Field(..., description="Name of the transition")
    timestamp: Optional[str] = Field(default=None, description="Transition timestamp")

