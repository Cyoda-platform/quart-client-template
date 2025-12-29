# Cyoda Starter Application — Functional Requirements

## 1. Project Overview
A starter Cyoda application scaffolded from the public template. This document captures functional and non-functional requirements to guide automatic code generation and incremental development.

## 2. Objectives
- Demonstrate a minimal event-driven Cyoda application.
- Provide entities, workflows, processors, and routes to support a simple Order lifecycle.
- Be production-ready for extension: observability, retries, idempotency, and basic auth.

## 3. Scope
Core scope for the initial build:
- Entities: Customer, Product, Order
- Workflows: OrderProcessing, CustomerOnboarding
- Events: OrderCreated, OrderValidated, PaymentProcessed, OrderShipped, CustomerCreated
- APIs: REST endpoints to create customers, create orders, query order status
- Integrations: Payment gateway (mock), Inventory service (mock)

## 4. Entities
- Customer
  - id: uuid (PK)
  - name: string
  - email: string
  - createdAt: iso8601 timestamp
  - status: enum (active, inactive)

- Product
  - id: uuid
  - sku: string
  - name: string
  - price: decimal
  - availableQuantity: integer

- Order
  - id: uuid
  - customerId: uuid
  - items: list of {productId: uuid, quantity: int, unitPrice: decimal}
  - totalAmount: decimal
  - currency: string
  - status: enum (created, validated, paid, shipped, cancelled)
  - createdAt: iso8601 timestamp
  - updatedAt: iso8601 timestamp

## 5. Events
- OrderCreated
  - payload: orderId, customerId, items, totalAmount, currency
  - produced by: Orders API

- OrderValidated
  - payload: orderId, valid: boolean, reason?
  - produced by: OrderValidation processor

- PaymentProcessed
  - payload: orderId, paymentId, amount, status
  - produced by: Payment processor

- OrderShipped
  - payload: orderId, shipmentId, carrier, tracking
  - produced by: Shipping processor

- CustomerCreated
  - payload: customerId, email, name
  - produced by: Customers API

## 6. Workflows
- OrderProcessing (initialState: created)
  - States:
    - created: on entry -> OrderValidation processor -> emit OrderValidated
    - validated: if valid -> PaymentProcessor -> emit PaymentProcessed
    - paid: -> InventoryReserve processor -> ShippingProcessor -> emit OrderShipped
    - shipped: terminal
    - cancelled: terminal
  - Retry policies: exponential backoff for external calls (payment, inventory)
  - Idempotency: processors must be idempotent for retries

- CustomerOnboarding (initialState: pending)
  - States:
    - pending: run EmailValidation processor -> CustomerCreated event
    - active: terminal
  - Validate email format and uniqueness

(Workflows should be represented as JSON files in application/workflow/ for the generator.)

## 7. APIs & Routes
- POST /customers
  - Request: {name, email}
  - Response: 201 {customerId}
  - Produces: CustomerCreated event

- POST /orders
  - Request: {customerId, items: [{productId, quantity}], currency}
  - Response: 202 {orderId}
  - Produces: OrderCreated event

- GET /orders/{orderId}
  - Response: 200 {order}

- Health & metrics
  - GET /health
  - GET /metrics

## 8. Processors & Integrations
- OrderValidation processor
  - Validates product availability and order schema
  - Emits OrderValidated

- PaymentProcessor (mock)
  - Simulates payment gateway call, returns success/failure
  - Emits PaymentProcessed

- InventoryReserve processor (mock)
  - Decrements availableQuantity or fails

- ShippingProcessor (mock)
  - Simulates shipping creation and emits OrderShipped

Integration details: abstract external dependencies behind interfaces so they can be mocked and replaced by real connectors.

## 9. Data Storage & Persistence
- Entities persisted as JSON documents (starter template patterns)
- Event store or message broker: in-memory or mock adapter for starter
- Ensure transactions or compensation strategies when necessary

## 10. Non-Functional Requirements
- Observability: logs (structured), metrics (basic counters), traces (optional)
- Scalability: stateless processors where possible; externalize state mechanisms
- Resilience: retry policies, circuit breakers for external calls (simulated)
- Security: basic input validation and authentication placeholder

## 11. Testing & Acceptance Criteria
- Unit tests for processors and workflow transitions
- Integration tests for API endpoints with mocked dependencies
- End-to-end flow: create order -> validate -> payment -> shipped
- Acceptance: sample script or Postman collection demonstrating flows

## 12. Deployment & Environment
- Use the Cyoda environment for local staging
- Provide Dockerfile and basic deployment descriptors in template
- Configurable via environment variables for external endpoints and credentials

## 13. Deliverables & Milestones
- M1: Scaffolded app with entities, workflows, and basic processors (this build)
- M2: REST API endpoints and simulated integrations
- M3: Tests and CI hooks

## 14. Assumptions
- This is a starter app; mocks are acceptable for external systems
- IDs are UUIDs
- Currency handling is simple decimal arithmetic

## 15. Next Steps
- Review and refine entities and workflows
- Choose to build automatically from these requirements or define entities/workflows incrementally

---

Generated by Cyoda starter assistant.