# Cyoda Starter Application (Python - Quart)

## Overview
A starter Cyoda application using the Python (Quart) template. This document captures functional requirements, core entities, workflows, APIs, and non-functional constraints to bootstrap development.

## Goals
- Provide a minimal, event-driven e-commerce order processing demo.
- Demonstrate entities, workflows, processors, and REST routes.
- Deployable using Cyoda environment with observability and retries.

## Primary Entities
1. Customer
   - id (string, uuid)
   - name (string)
   - email (string)
   - createdAt (datetime)

2. Product
   - id (string, uuid)
   - name (string)
   - sku (string)
   - price (decimal)
   - inventoryCount (integer)

3. Order
   - id (string, uuid)
   - customerId (string)
   - items (list of {productId, quantity, price})
   - totalAmount (decimal)
   - status (enum: CREATED, VALIDATED, PAID, FULFILLED, CANCELLED)
   - createdAt (datetime)

## Workflows
- OrderProcessingWorkflow
  - Initial state: CREATED
  - States: CREATED -> VALIDATED -> PAID -> FULFILLED
  - Error/Compensation: VALIDATION_FAILED, PAYMENT_FAILED, CANCELLED
  - Key processors: validateOrderProcessor, reserveInventoryProcessor, chargePaymentProcessor, notifyShipmentProcessor

## APIs / Routes
- POST /orders
  - Create a new order (triggers CREATED event)
- GET /orders/{id}
  - Retrieve order status and details
- POST /products
  - Add new product
- GET /products/{id}
  - Retrieve product details

## Events & Integrations
- Events: OrderCreated, OrderValidated, InventoryReserved, PaymentCharged, OrderFulfilled, OrderCancelled
- External integrations (simulated): Payment Gateway, Inventory Service, Notification Service

## Non-Functional Requirements
- Retry policies for transient failures (exponential backoff)
- Idempotency for processors that interact with external systems
- Logging and metrics for key events and processors
- Support concurrent processing and horizontal scaling

## Acceptance Criteria
- End-to-end order flow can be executed via REST API
- Workflows validated against workflow schema
- Basic unit tests for processors and entity validation

## Files to create (suggested)
- application/entity/customer/version_1/customer.json
- application/entity/product/version_1/product.json
- application/entity/order/version_1/order.json
- application/workflow/order_processing/version_1/order_processing.json
- application/processor/validate_order.py
- requirements/requirements.md (this file)

## Next Steps
1. Generate entities and workflows from this requirements file.
2. Build the application branch and run the setup assistant for deployment.

