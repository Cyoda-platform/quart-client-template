# Trading Desk Requirements — Phase 1 (Equities)

## Overview
A low-latency Order Management System (OMS) focused on equities. Phase 1 prioritizes core order lifecycle management, FIX connectivity, standard order types, and basic pre-trade controls. The system will be designed for modular growth into advanced execution and cross-venue routing in later phases.

## Functional Requirements

1. Order Lifecycle
   - Create, modify, cancel, and query orders via REST API and internal services.
   - Support synchronous and asynchronous order acknowledgements.
   - Order states: New, PartiallyFilled, Filled, Canceled, Rejected, PendingCancel.
   - Auditable events for each state transition with timestamp, actor, and correlation ID.

2. Order Types
   - Market, Limit, IOC (Immediate-Or-Cancel), FOK (Fill-Or-Kill), Stop.
   - Quantity and price validation.

3. Connectivity
   - FIX v4.2+ session management for buy-side execution connectivity.
   - Session recovery, heartbeats, and sequence number management.
   - Simple simulator for exchange connectivity for testing.

4. Pre-Trade Controls
   - Basic risk checks: max order size, order rate limits per user, symbol-level trading halts.
   - Validation of trading hours per exchange/venue.

5. Auditing & Persistence
   - All orders, events, FIX messages, and market acknowledgements stored for audit and rebuild.
   - Time-series storage for order events with millisecond resolution.

6. APIs
   - REST endpoints for order submission, modification, cancellation, and status queries.
   - WebSocket for real-time order event push to user dashboards.

7. Monitoring & Metrics
   - Latency metrics for order round-trip, FIX session latency, and processing pipeline.
   - Health endpoints and observability hooks (metrics & structured logs).

8. Testing & Simulation
   - Unit and integration tests for core order flows.
   - Simulation mode that substitutes real FIX sessions with a deterministic exchange simulator.

## Non-Functional Requirements

- Latency: Sub-second order processing end-to-end (target 10-200 ms depending on deployment).
- Throughput: Support bursts of up to 1,000 orders/sec in Phase 1 with horizontal scaling strategy.
- Durability: No single point of data loss; persisted to durable storage with replay capability.
- Security: OAuth2-based API authentication and granular RBAC.
- Compliance: Immutable audit logs for all order events.

## Phase 1 Out-of-Scope
- Advanced execution algos (TWAP/VWAP), multi-venue smart routing, derivatives support.

## Acceptance Criteria
- Successful creation, partial fill, fill, modification, and cancellation flows in simulated exchange tests.
- FIX connectivity test harness validates session establishment and sequence recovery.
- Pre-trade controls reject orders violating limits with clear error messages.
- Audit logs demonstrate full event traceability with millisecond timestamps.

## Notes
- Future phases will introduce execution algos, venue selection, and advanced risk engines.
