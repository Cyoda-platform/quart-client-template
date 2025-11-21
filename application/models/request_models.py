"""
Request Models for Customer API endpoints.

Provides comprehensive validation models for all API operations including
query parameters, request bodies, and response schemas.
"""

from __future__ import annotations

import re
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field, field_validator


class ErrorResponse(BaseModel):
    """Standard error response model."""

    error: str = Field(..., description="Error message")
    details: Optional[Dict[str, Any]] = Field(
        default=None, description="Additional error details"
    )
    code: Optional[str] = Field(default=None, description="Error code")


class SuccessResponse(BaseModel):
    """Standard success response model."""

    message: str = Field(..., description="Success message")
    data: Optional[Dict[str, Any]] = Field(default=None, description="Response data")


# Customer specific models
class CustomerQueryParams(BaseModel):
    """Query parameters for Customer endpoints."""

    name: Optional[str] = Field(default=None, description="Filter by customer name")
    email: Optional[str] = Field(default=None, description="Filter by customer email")
    state: Optional[str] = Field(
        default=None, description="Filter by workflow state", pattern=r"^[a-z_]+$"
    )
    page: int = Field(default=1, description="Page number", ge=1)
    page_size: int = Field(
        default=50, description="Number of results per page", ge=1, le=1000
    )

    # Computed properties for compatibility with existing pagination
    @property
    def limit(self) -> int:
        """Get limit for compatibility with existing code."""
        return self.page_size

    @property
    def offset(self) -> int:
        """Get offset for compatibility with existing code."""
        return (self.page - 1) * self.page_size

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: Optional[str]) -> Optional[str]:
        """Validate email format if provided."""
        if v is None:
            return v

        # Email format validation using regex
        email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        if not re.match(email_pattern, v):
            raise ValueError("Email must be a valid email address")

        return v.lower()


class CustomerUpdateQueryParams(BaseModel):
    """Query parameters for Customer update operations."""

    transition: Optional[str] = Field(
        default=None, description="Workflow transition to trigger", pattern=r"^[a-z_]+$"
    )


class TransitionRequest(BaseModel):
    """Request model for triggering workflow transitions."""

    transition_name: str = Field(
        ...,
        alias="transitionName",
        description="Name of the transition to execute",
        pattern=r"^[a-z_]+$",
    )

    @field_validator("transition_name")
    @classmethod
    def validate_transition_name(cls, v: str) -> str:
        """Validate transition name format."""
        if not v or len(v.strip()) == 0:
            raise ValueError("Transition name cannot be empty")
        return v.strip().lower()


class SearchRequest(BaseModel):
    """Request model for customer search operations."""

    name: Optional[str] = Field(default=None, description="Search by customer name")
    email: Optional[str] = Field(default=None, description="Search by customer email")
    phone: Optional[str] = Field(default=None, description="Search by customer phone")
    address: Optional[str] = Field(
        default=None, description="Search by customer address"
    )
    state: Optional[str] = Field(default=None, description="Search by workflow state")

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: Optional[str]) -> Optional[str]:
        """Validate email format if provided."""
        if v is None:
            return v

        # Email format validation using regex
        email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        if not re.match(email_pattern, v):
            raise ValueError("Email must be a valid email address")

        return v.lower()


class CustomerCreateRequest(BaseModel):
    """Request model for creating customers."""

    name: str = Field(
        ..., description="Customer full name", min_length=2, max_length=100
    )
    email: str = Field(..., description="Customer email address", max_length=255)
    phone: Optional[str] = Field(
        default=None, description="Customer phone number", max_length=20
    )
    address: Optional[str] = Field(
        default=None, description="Customer address", max_length=500
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate name field."""
        if not v or len(v.strip()) == 0:
            raise ValueError("Name must be non-empty")
        return v.strip()

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        """Validate email field with format validation."""
        if not v or len(v.strip()) == 0:
            raise ValueError("Email must be non-empty")

        # Email format validation using regex
        email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        if not re.match(email_pattern, v.strip()):
            raise ValueError("Email must be a valid email address")

        return v.strip().lower()

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: Optional[str]) -> Optional[str]:
        """Validate phone field if provided."""
        if v is None or len(v.strip()) == 0:
            return None

        # Basic phone validation
        phone_pattern = r"^[\d\s\-\(\)\+\.]+$"
        if not re.match(phone_pattern, v.strip()):
            raise ValueError(
                "Phone must contain only digits, spaces, hyphens, parentheses, and plus signs"
            )

        return v.strip()

    @field_validator("address")
    @classmethod
    def validate_address(cls, v: Optional[str]) -> Optional[str]:
        """Validate address field if provided."""
        if v is None or len(v.strip()) == 0:
            return None

        return v.strip()


class CustomerUpdateRequest(BaseModel):
    """Request model for updating customers."""

    name: Optional[str] = Field(
        default=None, description="Customer full name", min_length=2, max_length=100
    )
    email: Optional[str] = Field(
        default=None, description="Customer email address", max_length=255
    )
    phone: Optional[str] = Field(
        default=None, description="Customer phone number", max_length=20
    )
    address: Optional[str] = Field(
        default=None, description="Customer address", max_length=500
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: Optional[str]) -> Optional[str]:
        """Validate name field if provided."""
        if v is None:
            return v
        if len(v.strip()) == 0:
            raise ValueError("Name must be non-empty")
        return v.strip()

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: Optional[str]) -> Optional[str]:
        """Validate email field if provided."""
        if v is None:
            return v
        if len(v.strip()) == 0:
            raise ValueError("Email must be non-empty")

        # Email format validation using regex
        email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        if not re.match(email_pattern, v.strip()):
            raise ValueError("Email must be a valid email address")

        return v.strip().lower()

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: Optional[str]) -> Optional[str]:
        """Validate phone field if provided."""
        if v is None or len(v.strip()) == 0:
            return None

        # Basic phone validation
        phone_pattern = r"^[\d\s\-\(\)\+\.]+$"
        if not re.match(phone_pattern, v.strip()):
            raise ValueError(
                "Phone must contain only digits, spaces, hyphens, parentheses, and plus signs"
            )

        return v.strip()

    @field_validator("address")
    @classmethod
    def validate_address(cls, v: Optional[str]) -> Optional[str]:
        """Validate address field if provided."""
        if v is None or len(v.strip()) == 0:
            return None

        return v.strip()
