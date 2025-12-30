# Project: [Your Project Name]

## 1. Overview
A Cyoda-based event-driven application scaffolded from the official template. This document captures the initial functional requirements to kick off development. Replace placeholders ([...]) with project-specific details.

## 2. Purpose and Goals
- Primary purpose: [e.g., process orders, manage customer lifecycle, handle notifications]
- Key goals:
  - Reliable event-driven processing
  - Clear entity models for core business objects
  - Reusable processors and workflows
  - Observability and retry/resilience for failed processing

## 3. Users & Personas
- System (background processors)
- Admin: manage reference data and monitor workflows
- API clients: external systems producing/consuming events

## 4. High-level Features
- Ingest events via HTTP or message broker
- Validate and enrich incoming events
- Orchestrate stateful workflows per entity (e.g., Order lifecycle)
- Persist entity snapshots and emit domain events
- Error handling, retries, dead-letter handling
- Admin endpoints for inspection and manual retries

## 5. Core Entities (initial)
List core entities and example JSON instances. Create entity files under application/entity/<entity>/version_1/

- Customer
  - Example: {"id": "cust_001", "name": "Jane Doe", "email": "jane@example.com"}
- Order
  - Example: {"id": "ord_001", "customerId": "cust_001", "items": [{"sku": "sku_123", "qty": 2}], "status": "created"}
- Product
  - Example: {"id": "sku_123", "name": "Widget", "price": 9.99}

(Adjust fields per your domain.)

## 6. Workflows
Define workflows that manage entity lifecycles. Examples:
- OrderProcessing: initialState: created -> paid -> shipped -> completed -> cancelled
- CustomerOnboarding: initialState: pending -> verified -> active

Include processors for validation, payment processing integration, and fulfillment.

## 7. Events & Contracts
- Input events: OrderCreated, PaymentReceived, InventoryReserved
- Output events: OrderPaid, OrderShipped, OrderCompleted, OrderFailed

Specify event schemas and versioning strategy.

## 8. Integration Points
- External payment service: [API endpoint placeholder]
- Inventory system: [API endpoint placeholder]
- Webhooks / API consumers

## 9. Non-functional Requirements
- Resilience: retry policies for transient failures
- Observability: logs, metrics, and tracing for long-running workflows
- Performance: target throughput [e.g., 100 req/s]
- Security: authenticated admin endpoints and secure service-to-service communication

## 10. Acceptance Criteria
- End-to-end OrderProcessing workflow completes for happy path
- Failed processing retries and lands in dead-letter with manual retry option
- Entities persisted and retrievable via admin endpoints

## 11. Next Steps / Roadmap
1. Create concrete entity JSON files for Customer, Order, Product (version_1)
2. Draft OrderProcessing workflow JSON and validate against workflow schema
3. Implement processors for validation and payment integration
4. Run template application locally and execute sample events

## 12. Notes
- Use semantic versioning for entity and workflow model versions
- Keep workflows small and single-responsibility
- Document processors with example inputs/outputs

---
Generated from: Cyoda template initialization
