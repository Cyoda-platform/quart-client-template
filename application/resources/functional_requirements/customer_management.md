# Customer Management - Functional Requirements

## Overview
Provide a REST API to manage customers with full CRUD operations, input validation, and persistence.

## API Endpoints
- POST /customers - Create customer
- GET /customers - List customers (pagination support)
- GET /customers/{id} - Retrieve customer by id
- PUT /customers/{id} - Update customer
- DELETE /customers/{id} - Delete customer (logical delete: sets status to 'inactive' or 'deleted')

## Customer Model
- id: uuid (generated)
- name: string (required)
- email: string (required, valid email, unique)
- phone: string (optional)
- address: string (optional)
- status: ENUM [active, inactive, deleted] (default: active)
- created_at: datetime (generated)
- updated_at: datetime (updated on changes)

## Validation
- name and email are required
- email must be a valid email format
- email must be unique

## Persistence
- Use the application's built-in storage providers in Cyoda templates (file-based or embedded store depending on template)

## Behavior
- Create sets created_at and updated_at and status=active
- Update updates updated_at
- Delete sets status=deleted and updated_at

## Workflow
Use the CustomerLifecycle workflow with states: created → active/inactive → deleted

## Non-functional
- Concurrency: Ensure idempotent create and update operations where appropriate
- Error handling: Return appropriate HTTP status codes and error messages
