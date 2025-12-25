# Customer Management API - Functional Requirements

Overview

This service provides a REST API for managing customers with full CRUD operations.

Entities

- Customer
  - id (string)
  - firstName (string)
  - lastName (string)
  - email (string, email format)
  - phone (string)
  - createdAt (date-time)
  - status (string) - ACTIVE or DELETED

API Endpoints (HTTP/JSON)

- POST /customers
  - Create a new customer
  - Request body: Customer object without id and createdAt
  - Response: 201 Created with Customer object including id and createdAt

- GET /customers
  - List customers (supports pagination)
  - Response: 200 OK with list of Customer objects

- GET /customers/{id}
  - Retrieve a single customer by id
  - Response: 200 OK with Customer object or 404 Not Found

- PUT /customers/{id}
  - Update a customer's information
  - Request body: Customer fields to update
  - Response: 200 OK with updated Customer object or 404 Not Found

- DELETE /customers/{id}
  - Soft-delete a customer (set status=DELETED)
  - Response: 204 No Content on success or 404 Not Found

Business Rules

- Email must be unique across customers.
- Soft delete should mark status as DELETED and preserve record for audit.
- Restoring a deleted customer is supported via workflow (restore transition).

Data Validation

- Validate email format and required fields (firstName, lastName, email).

Notes

- Persistence will be implemented using the Cyoda platform storage abstractions.
- The API will return standard HTTP status codes and JSON bodies.
