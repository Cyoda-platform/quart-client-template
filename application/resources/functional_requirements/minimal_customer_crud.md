# Minimal requirements - Customer CRUD only

## Overview
A minimal application to manage Customers with basic create, read, update, and delete operations.

## Entities
- Customer: id (string), name (string), email (string), phone (string)

## APIs
- POST /customers — create a customer
- GET /customers — list customers
- GET /customers/{id} — get customer by id
- PUT /customers/{id} — update customer
- DELETE /customers/{id} — delete customer

## Constraints
- id is unique
- email must be a valid email format

## Non-functional
- Built with Cyoda Python template
