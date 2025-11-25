# Order Management Functional Requirements

## Overview

The Order management feature allows creating, updating, and cancelling customer orders. Orders contain customer references, line items, totals, currency, shipping address, and status tracking.

## Main Scenarios

### 1) Create Order
- Endpoint: POST /orders
- Input: customer_id, items, currency, shipping_address
- Behavior:
  - Validate input (customer exists, items valid, positive quantities)
  - Calculate total_amount (sum item quantity * unit_price)
  - Set status to CREATED
  - Persist the Order entity
  - Trigger OrderWorkflow transition: create
- Output: 201 Created with order id and order summary

### 2) Update Order
- Endpoint: PATCH /orders/{id}
- Input: Fields to update (items, shipping_address, currency)
- Behavior:
  - Validate the order exists and is in a modifiable state (CREATED)
  - Apply updates and recalculate total_amount if items changed
  - Update status to UPDATED
  - Persist changes
  - Trigger OrderWorkflow transition: update
- Output: 200 OK with updated order summary

### 3) Cancel Order
- Endpoint: POST /orders/{id}/cancel
- Input: Cancel reason (optional)
- Behavior:
  - Validate the order exists and is cancellable (CREATED or UPDATED)
  - Set status to CANCELLED
  - Record cancellation reason and timestamp
  - Persist changes
  - Trigger OrderWorkflow transition: cancel
- Output: 200 OK with cancellation confirmation

## Data Model
- Order (as defined in entity/order/version_1/order.json)

## Workflow
- Use OrderWorkflow: create -> created, update -> updated, cancel -> cancelled

## Processors
- AttachEntityProcessor: Attaches entity payload to workflow execution
- UpdateOrderProcessor: Validates and applies updates, recalculates totals
- CancelOrderProcessor: Validates cancellability and marks order cancelled

## API Contracts
- Request/response examples should follow JSON schema derived from the Order entity

## Security
- Endpoints require authentication
- Authorization: only owners or admins can update/cancel orders

## Non-functional
- Ensure idempotency for create requests using client-provided idempotency key
- Validate & sanitize all inputs

## Future Enhancements
- Add payment capture workflow after order creation
- Support partial cancellations and refunds
