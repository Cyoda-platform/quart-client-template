# Customer Management (CRUD)

## Overview

Provide functionality to create, read, update, and delete customer records. Support searching and pagination for listing customers. Ensure data validation and proper error handling for user inputs.

## Functional Requirements

1. Create Customer
   - Endpoint: POST /customers
   - Input: name (required), email (required, valid email), phone (optional)
   - Behavior: Validate inputs, create a new customer with a generated UUID, return 201 Created with customer payload.

2. Retrieve Customer
   - Endpoint: GET /customers/{id}
   - Behavior: Return customer by id. If not found, return 404 Not Found.

3. Update Customer
   - Endpoint: PUT /customers/{id}
   - Input: name, email, phone (all optional except at least one must be present)
   - Behavior: Validate inputs, apply updates, return 200 OK with updated payload. If not found, return 404.

4. Delete Customer
   - Endpoint: DELETE /customers/{id}
   - Behavior: Delete customer, return 204 No Content. If not found, return 404.

5. List Customers
   - Endpoint: GET /customers
   - Query params: page (default 1), per_page (default 20), search (optional, matches name/email)
   - Behavior: Return paginated list of customers with metadata (total, page, per_page).

6. Search
   - Endpoint: GET /customers?search=term
   - Behavior: Search customers by name or email containing the term, case-insensitive.

## Non-Functional Requirements

- Input validation: emails must be validated; phone numbers normalized.
- Error handling: consistent error response format with code and message.
- Security: endpoints should require authentication (token-based) in non-dev environments.
- Auditing: log create/update/delete actions with user and timestamp.

## Events

- CustomerCreated: emitted after successful creation with customer payload.
- CustomerUpdated: emitted after update.
- CustomerDeleted: emitted after deletion.

## Notes

- Integrate with CustomerOnboarding workflow for initial onboarding steps (email verification, welcome notification).