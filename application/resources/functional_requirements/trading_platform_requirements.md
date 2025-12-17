# Real-time Trading Platform — Functional Requirements

## 1. Overview

This document describes the functional requirements for a real-time trading platform supporting equities and derivatives. The platform is event-driven and built on Cyoda’s architecture to provide market data ingestion, order management, portfolio and P&L tracking, risk controls, compliance workflows, durable persistence, and replay/restore capabilities.

## 2. Scope and Goals

- Support market data ingestion from multiple feeds (equities, futures, options)
- Normalize and enrich market data into a canonical format
- Provide an Order Management System (OMS) with lifecycle events, routing, and execution integration
- Maintain portfolio, position, and P&L in real-time with event sourcing for auditability
- Implement pre-trade and real-time risk checks with limits and alerting
- Provide compliance workflows, audit trails, and regulatory reporting exports
- Ensure durable persistence, replay, and restore for recovery and backtesting
- Design for low latency, scalability, and operational observability

## 3. Actors and Roles

- Trader: Submits orders, views positions and P&L
- Algo Engine: Subscribes to market data and submits orders
- Exchange/Execution Venue: External system for order execution and fills
- Market Data Provider: Feeds market data events
- Risk Manager: Configures limits and reviews alerts
- Compliance Officer: Reviews audit trail and generates reports
- System Operator: Monitors system health and manages deployments

## 4. High-Level Architecture

- Event Bus: Central event streaming backbone for all domain events
- Ingestors: Adapters for market data feeds and execution reports
- Normalizer: Converts incoming feeds to canonical market data events
- Order Service: Handles order lifecycle, state machine, and routing
- Execution Adapter: Connectors to external/exchange APIs
- Portfolio Service: Calculates positions, exposures, and P&L
- Risk Engine: Synchronous and asynchronous checks for pre-trade and post-trade
- Compliance Service: Captures audit trails, stores immutable events, generates reports
- Persistence: Event store and durable storage for snapshots and replay
- Monitoring & Alerts: Metrics, logs, traces, and alerting hooks

## 5. Functional Requirements

### 5.1 Market Data Ingestion & Normalization
- Connect to multiple market data providers via adapters (FIX/FAST, WebSocket, REST)
- Parse feed-specific messages, handle sequence gaps, and re-sequencing
- Normalize into canonical tick and orderbook events:
  - Tick: {instrument_id, timestamp, bid, ask, last_price, volume, source}
  - OrderBook: {instrument_id, timestamp, bids[], asks[], depth}
- Support snapshot and incremental updates
- Recover from feed disconnects and replay missing messages
- Enrich ticks with reference data (symbol mapping, exchange metadata)

### 5.2 Order Management System (OMS)
- Order lifecycle states: NEW, PENDING, ACKNOWLEDGED, PARTIALLY_FILLED, FILLED, CANCELLED, REJECTED
- Accept order types: Market, Limit, Stop, Stop-Limit, IOC, GTC
- Support order modification and cancellation
- Route orders to execution adapters with configurable routing rules
- Persist order events for audit and replay
- Correlate execution reports and fills back to orders
- Expose synchronous API for order submission and asynchronous event notifications

### 5.3 Portfolio, Positions & P&L
- Track positions per account, per instrument, and aggregated across portfolios
- Real-time mark-to-market using canonical market data events
- Calculate realized and unrealized P&L, average price, and cost basis
- Support position limits, shorts, margin calculations for derivatives
- Snapshotting and snapshot restore for fast recovery

### 5.4 Risk Controls
- Pre-trade checks: order size limits, position limits, max notional, instrument restrictions
- Real-time checks: intraday exposure, concentrated risk, margin thresholds
- Plug-in architecture for custom risk rules
- Alerts and automated mitigations (reject, warn, throttle)
- Audit of risk overrides and approvals

### 5.5 Compliance & Reporting
- Immutable audit trail of all domain events with timestamps and actor metadata
- Export formats: CSV/JSON and regulatory formats required by exchanges
- Workflow for suspicious activity review and escalation
- Retention policies and data archival

### 5.6 Persistence, Replay & Recovery
- Append-only event store for domain events
- Snapshots for quick state reconstruction
- Tools for replaying events into the system for backtesting and recovery
- Consistent ordering and idempotency guarantees

### 5.7 Scalability, Latency & Observability
- Horizontal scalability for ingestors, OMS, portfolio, and risk engines
- Low-latency processing paths for market data and order execution
- Metrics and tracing on critical paths (latency histograms, error rates)
- Health checks and self-healing patterns

### 5.8 Testing & Simulation Harness
- Market simulator to feed synthetic ticks and execution reports
- Integration tests for order flows and risk checks
- Load tests to validate throughput and latency

## 6. Non-functional Requirements

- High availability (active/active across zones)
- Secure authentication and authorization for APIs
- Encryption at rest and in transit for sensitive data
- Auditable configuration changes
- Disaster recovery RTO/RPO targets

## 7. Acceptance Criteria
- Can ingest and normalize market data from at least two feed formats
- OMS can accept, modify, cancel orders and persist lifecycle events
- Portfolio service shows real-time P&L updates on market ticks
- Pre-trade risk rejects orders that exceed configured limits
- Audit trail can produce a regulatory export for a day of activity
- System can replay events to reconstruct end-of-day state

## 8. Next Steps (Design → Build)
1. Define Entities (in Canvas): Instrument, Order, OrderEvent, Fill, Position, Portfolio, RiskRule, AuditEvent
2. Create Workflows: Order lifecycle, Fill processing, Position updates, Compliance review
3. Add detailed requirements for adapters and execution connectors
4. Generate application code from Canvas and run build


---
Generated by Cyoda GitHub Agent
