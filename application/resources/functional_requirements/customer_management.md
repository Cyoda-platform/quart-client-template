# Customer Management Functional Requirements

## Overview
Build a REST API that provides CRUD operations for managing customers. The API will support creating, retrieving, updating, deleting, and listing customers. It should include validation, pagination for list endpoints, and basic search/filtering by name or email.

## Requirements
- Entities:
  - Customer: id, firstName, lastName, email, phone, address (street, city, state, zip), createdAt, status
- REST Endpoints:
  - POST /customers — Create customer
  - GET /customers/{id} — Retrieve customer by id
  - PUT /customers/{id} — Update customer
  - DELETE /customers/{id} — Delete customer
  - GET /customers — List customers with pagination and optional filters: name, email
- Validation:
  - email must be valid
  - firstName and lastName required
  - phone optional but must match pattern if provided
- Persistence:
  - Use Cyoda-provided data storage (handled during deploy)
- Tests:
  - Unit tests for service layer
  - Integration tests for API endpoints

## Security
- API should include basic authentication/authorization (to be configured during deploy).

## Non-functional
- Proper error handling with standard HTTP status codes
- JSON request/response

