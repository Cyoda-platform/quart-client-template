# Customer Management REST API - Functional Requirements

## Overview
Provide a REST API to manage customers with full CRUD: create, read (single and list), update, delete.

## Endpoints
- POST /customers — Create a customer
- GET /customers — List customers (supports pagination)
- GET /customers/{id} — Get customer by id
- PUT /customers/{id} — Update customer
- DELETE /customers/{id} — Delete customer

## Customer model
- id (string)
- name (string)
- email (string)
- phone (string)
- address (object: street, city, state, zip)
- createdAt (datetime)
- status (enum: ACTIVE, DELETED)

## Behavior
- Create returns 201 with location header
- Update returns 200 with updated resource
- Delete marks status=DELETED and returns 204
- Validation: email required and must be valid; name required

## Notes
- Stateless REST API
- Use in-memory or lightweight datastore for dev
- Provide unit tests and example curl commands
