# Customer Functional Requirements

## Overview
The Customer entity represents a user/customer with contact information used across the system. This document outlines the primary use cases and API expectations.

## Entity
Customer (fields):
- id: string (unique identifier)
- name: string
- email: string (valid email format)
- phone: string (E.164 recommended)

## Use Cases
1. Create Customer
   - Endpoint: POST /customers
   - Payload: {name, email, phone}
   - Behavior: Validate input, persist Customer, return 201 with Customer resource including generated id.

2. Get Customer
   - Endpoint: GET /customers/{id}
   - Behavior: Retrieve Customer by id. Return 200 with Customer or 404 if not found.

3. Update Customer
   - Endpoint: PUT /customers/{id}
   - Payload: {name?, email?, phone?}
   - Behavior: Validate and update fields. Return 200 with updated Customer.

4. Delete Customer
   - Endpoint: DELETE /customers/{id}
   - Behavior: Soft-delete or mark as deleted. Return 204 on success.

## Validation Rules
- email must be a valid email address
- phone should conform to E.164 format when possible
- name should not be empty and less than 255 characters

## Error Handling
- 400 Bad Request for validation errors with details
- 404 Not Found when resource is missing
- 500 Internal Server Error for unexpected failures

## Data Retention
- Soft deletes should mark records as deleted; actual removal occurs after X days (configurable)

## Security
- Endpoints must be protected by API keys or OAuth; only authorized services can modify Customer data

## Notifications (optional)
- On customer creation, send a welcome email (processor can be added to workflow)
