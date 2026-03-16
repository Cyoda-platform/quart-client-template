# Customer Management API - Minimal CRUD

## Goal
Provide a minimal REST API for managing customers with the following fields and behaviors:

- id (UUID) - primary identifier
- first_name (string)
- last_name (string)
- email (string)
- phone (string)

## Endpoints
- POST /customers — create a new customer
- GET /customers — list customers
- GET /customers/{id} — retrieve customer by id
- PUT /customers/{id} — update an existing customer
- DELETE /customers/{id} — delete a customer

## Constraints & Notes
- No authentication required
- Use lightweight persistence (in-memory or simple SQLite)
- Basic validation: required fields (first_name, last_name, email); email format
- Return standard HTTP status codes (201 created, 200 ok, 404 not found, 400 bad request)
