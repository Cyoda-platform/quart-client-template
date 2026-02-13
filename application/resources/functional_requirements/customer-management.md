# Customer Management API - Functional Requirements

Overview
--------

We will build a Python-based REST API for Customer Management that provides Create, Read, Update, and Delete (CRUD) operations.

Scope
-----
- Entities: Customer
- Operations: Create Customer, Get Customer by ID, List Customers, Update Customer, Delete Customer (soft delete)
- Validation: Basic input validation for required fields and formats
- Persistence: Cyoda-managed durable storage
- Authentication: API Key-based access control (managed by Cyoda)
- Tests: Unit tests covering service layer and route handlers

Functional Requirements
-----------------------
1. Create Customer
   - POST /customers
   - Request body: name (string, required), email (string, required, valid email), phone (string, optional)
   - Response: 201 Created with customer object including id, createdAt, createdBy

2. Get Customer
   - GET /customers/{id}
   - Response: 200 OK with customer object or 404 Not Found

3. List Customers
   - GET /customers
   - Response: 200 OK with list of customers (paginated default: 50)

4. Update Customer
   - PUT /customers/{id}
   - Request body: name, email, phone
   - Response: 200 OK with updated customer object or 404 Not Found

5. Delete Customer (Soft Delete)
   - DELETE /customers/{id}
   - Behavior: Mark customer as deleted; do not remove from storage
   - Response: 204 No Content

Non-Functional Requirements
---------------------------
- API must be built using Cyoda Python template (quart-based service)
- Config-driven API Key auth via environment managed by Cyoda
- Logging and basic metrics hooks
- Code style: Black/Flake8 compatible

Notes
-----
- This initial scope targets a managed storage solution for persistence and an API Key model for access. Environment configuration (API keys, storage credentials) will be managed within the Cyoda environment configuration later.
