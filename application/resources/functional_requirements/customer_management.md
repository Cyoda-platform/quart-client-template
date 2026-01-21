# Customer Management API - Functional Requirements

## Overview
Build a minimal customer-management REST API with CRUD operations.

## Scope
- Entities: Customer
- Fields: id (UUID), name (string), email (string), phone (string)
- Basic validation: required fields (name, email), email format validation, phone optional

## Endpoints
- POST /customers -> Create a customer
- GET /customers -> List all customers
- GET /customers/{id} -> Get customer by id
- PUT /customers/{id} -> Update customer
- DELETE /customers/{id} -> Delete customer

## Data Storage
- In-memory store for simplicity (suitable for a minimal demo). Persist to JSON file if requested.

## Response codes
- 201 Created, 200 OK, 204 No Content, 400 Bad Request, 404 Not Found

## Non-functional
- Simple, well-documented, and easily extensible
