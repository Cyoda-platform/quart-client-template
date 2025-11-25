# Customer — Functional Requirements

## Purpose
Describe the Customer entity and the functional requirements needed to manage customer records and contact information.

## Actors
- System Administrators
- External Clients (API consumers)
- Internal Services (billing, notifications)

## Scope
Manage creation, retrieval, update, and deletion of customer records. Provide validation, uniqueness, and basic search/filter capabilities.

## Entity Fields
- id (string, uuid) — Unique identifier for the customer (required)
- name (string) — Full name of the customer (required)
- email (string, email) — Customer email address (required, unique, validated)
- phone (string) — Phone number (optional, validated format)

## Functional Requirements
1. Create Customer
   - Endpoint: POST /customers
   - Accepts: name, email, phone
   - Generates: id (UUID) if not provided
   - Validations: email format, required fields (name, email), email uniqueness
   - Response: 201 Created with customer resource

2. Retrieve Customer
   - Endpoint: GET /customers/{id}
   - Returns: Customer resource or 404 if not found

3. Update Customer
   - Endpoint: PUT /customers/{id}
   - Accepts: name, email, phone
   - Validations: email format, email uniqueness across customers (unless same record)
   - Response: 200 OK with updated resource

4. Delete Customer
   - Endpoint: DELETE /customers/{id}
   - Soft-delete preferred (configurable), response 204 No Content

5. List/Search Customers
   - Endpoint: GET /customers
   - Supports: pagination (limit, offset), filtering by name/email, sorting

6. Events
   - Emit events on create/update/delete: customer.created, customer.updated, customer.deleted
   - Event payload should include id and relevant fields

## Acceptance Criteria
- Creating a customer with valid data returns 201 and persistent resource
- Duplicate emails are rejected with a clear error
- Retrieving an existing customer returns accurate data
- Updating email enforces uniqueness and validation
- Deleting a customer prevents retrieval but preserves an audit trail if soft-delete

## Security & Privacy
- Validate and sanitize all inputs
- Store email and phone securely, comply with data protection policies
- Access control: only authorized services/users may create/update/delete

## Non-Functional
- API responses should be under 500ms under typical load
- System should handle up to expected customer volume (TBD)

## Example Customer JSON
{
  "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "name": "Jane Doe",
  "email": "jane.doe@example.com",
  "phone": "+1-555-123-4567"
}
