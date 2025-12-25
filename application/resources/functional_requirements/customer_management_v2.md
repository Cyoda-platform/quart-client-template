# Customer Management - Functional Requirements (v2)

Summary

Provide a REST API for Customer entity with full CRUD operations, validation, and soft-delete behavior.

Entities

Customer
- id: string (generated UUID)
- firstName: string (required)
- lastName: string (required)
- email: string (required, unique, email format)
- phone: string (optional)
- createdAt: date-time (generated)
- status: string (ACTIVE, DELETED)

API Endpoints

POST /customers
- Create a customer
- Request: JSON with firstName, lastName, email, phone
- Response: 201 Created with full Customer object

GET /customers
- List customers
- Query params: page, size, status (optional)
- Response: 200 OK, paginated list of customers

GET /customers/{id}
- Retrieve a customer by id
- Response: 200 OK with Customer object or 404 if not found

PUT /customers/{id}
- Update a customer's fields (firstName, lastName, email, phone)
- Email must remain unique
- Response: 200 OK with updated Customer object or 404 if not found

DELETE /customers/{id}
- Soft-delete: set status=DELETED
- Response: 204 No Content or 404 if not found

Business Rules

- Email uniqueness enforced at persistence layer
- Soft-delete retains record for audit; restore supported via workflow
- Validation: firstName, lastName, email required; email format validated

Error Handling

- 400 Bad Request for validation errors
- 404 Not Found when resource does not exist
- 409 Conflict when attempting to create/update with an email that already exists

Security & Auth

- API should be secured; authentication/authorization will be implemented in deployment

Notes

- Persistence will use Cyoda platform storage abstractions
- Follow standard HTTP codes and JSON responses
