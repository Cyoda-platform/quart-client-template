# Customer Management API - Functional Requirements

## Overview
Provide a RESTful Customer Management API with full CRUD operations. The API will be part of a Cyoda application and persist customer data to the application's storage layer. It must include input validation, pagination and filtering for listing customers, and example unit/integration tests.

## API Endpoints

1. Create Customer
   - POST /api/customers
   - Request body: JSON with firstName, lastName, email, phone (optional), address (object)
   - Validation: firstName (required), lastName (required), email (required, email format), phone (optional, phone format), address.line1 (required), address.city, address.country
   - Response: 201 Created with created customer JSON including id, createdAt, updatedAt

2. Get Customer
   - GET /api/customers/{id}
   - Response: 200 OK with customer JSON or 404 Not Found

3. List Customers
   - GET /api/customers
   - Query params: page (default 1), size (default 20), sort (e.g., createdAt:asc), filter (e.g., email, lastName)
   - Response: 200 OK with paginated list {items: [...], page, size, total}

4. Update Customer
   - PUT /api/customers/{id}
   - Request body: fields to update (firstName, lastName, email, phone, address)
   - Validation: same as create for required fields if present; email must remain unique
   - Response: 200 OK with updated customer JSON

5. Delete Customer
   - DELETE /api/customers/{id}
   - Response: 204 No Content on success; 404 if not found

## Data Model
Customer entity is already defined in Canvas. Use that entity for persistence.

## Storage
Persist data to the Cyoda application's storage (managed by Cyoda runtime). The repository should include repository-layer code or processors to persist entities to the app storage.

## Validation
- Use server-side validators for fields (email regex, phone pattern)
- Ensure unique email across customers (enforce in persistence layer)

## Pagination & Filtering
- Implement standard offset-based pagination with page/size
- Support simple filtering by email and lastName
- Support sorting by createdAt and updatedAt

## Tests
- Unit tests for validation and processor logic
- Integration tests for REST endpoints (create → get → update → delete)
- Tests should run as part of the repository test suite (e.g., pytest)

## Examples
Provide example request/response payloads in the docs and example tests.

## Non-functional
- Reasonable performance for small-medium datasets
- Clear error messages and HTTP status codes

# Next Steps
- Implement processors and REST routes to meet these requirements
- Add unit and integration tests
