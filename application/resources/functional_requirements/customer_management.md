# Customer Management - Functional Requirements

## Overview
The Customer Management module handles creation, update, retrieval, and archival (soft-delete) of customer records. It integrates with the rest of the Cyoda system through events and workflows and exposes APIs for external clients.

## Goals
- Provide a clear lifecycle for Customer entities (Created -> Active -> Deleted).
- Ensure data validation for required fields and email format.
- Support soft-delete to allow archiving and potential recovery.
- Emit events for create, update, and delete operations to enable downstream processing.

## Stakeholders
- Product Owners
- Backend Engineers
- QA Engineers
- Integrations Team

## Entities
- Customer
  - id (string, required, unique) - UUID
  - name (string, required)
  - email (string, required, valid email)
  - phone (string, optional, E.164 preferred)

## Workflows
- CustomerWorkflow
  - States: Created, Active, Deleted
  - Transitions: create_customer, update_customer, delete_customer
  - Events: CustomerCreated, CustomerUpdated, CustomerDeleted

## API Endpoints
- POST /customers
  - Description: Create a new customer
  - Request body: { name, email, phone }
  - Response: 201 Created with created customer payload
  - Emits: CustomerCreated event

- GET /customers/{id}
  - Description: Retrieve customer by id
  - Response: 200 OK or 404 Not Found

- PUT /customers/{id}
  - Description: Update an existing customer
  - Request body: partial fields to update
  - Response: 200 OK with updated customer
  - Emits: CustomerUpdated event

- DELETE /customers/{id}
  - Description: Soft-delete (archive) a customer
  - Response: 204 No Content
  - Emits: CustomerDeleted event

## Events & Payloads
- CustomerCreated
  - payload: { id, name, email, phone }
- CustomerUpdated
  - payload: { id, changes }
- CustomerDeleted
  - payload: { id }

## Validation Rules
- id: must be UUID
- name: non-empty
- email: valid email format
- phone: optional, prefer E.164 format

## Persistence
- Store Customer entity in primary datastore (e.g., PostgreSQL)
- Soft-delete implemented via `deleted_at` timestamp or `is_deleted` flag

## Security
- Endpoints require authentication (JWT/OAuth)
- Only authorized users/services can create, update, or delete customers

## Monitoring & Observability
- Track counts of created, updated, deleted events
- Log validation failures and exceptions

## Testing
- Unit tests for processors and validation
- Integration tests for API endpoints and event emission
- E2E tests for workflow transitions

## Non-functional Requirements
- API latency under 200ms for common operations
- High availability: 99.9% uptime for Customer APIs

## Open Questions
- Should we blacklist certain email domains?
- How long should archived records be retained?

## Glossary
- Soft-delete: mark entity as deleted without physically removing from DB
