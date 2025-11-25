# Order Management Functional Requirements

## Overview
Create a workflow-driven Order entity supporting create, update, and cancel operations.

## Entities
- Order: id, status, items, total, customerId

## Workflows
- OrderWorkflow
  - create: transition from initial_state to created. Persists order.
  - update: transition from created to updated. Applies updates to order.
  - cancel: transition from created to cancelled. Triggers cancellation process.

## Processors
- persist_order: Persist new order to storage; emit OrderCreated event.
- update_order: Apply updates and emit OrderUpdated event.
- cancel_order: Mark order as cancelled, emit OrderCancelled event, notify downstream systems.

## API
- POST /orders - create order
- PUT /orders/{id} - update order
- POST /orders/{id}/cancel - cancel order

## Validation
- Ensure total >= 0
- Items array must not be empty for create

## Non-functional
- Processors should be idempotent
- Responses should be returned within 200ms for sync processors
- Async cancel may be eventually consistent
