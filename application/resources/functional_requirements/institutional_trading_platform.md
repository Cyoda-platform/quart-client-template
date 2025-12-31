# Institutional Trading Platform — Functional Requirements

Version: 1.0  
Status: Draft  
Owner: Trading Platform Team  

## 1. Overview
Build an institutional-grade trading platform supporting real-time market data, advanced order management, portfolio and position tracking, pre- and post-trade risk controls, regulatory compliance, and real-time P&L for equities and derivatives (futures, options). The platform will be event-driven and designed for high throughput, low latency, auditability, and operational resilience.

## 2. Goals and Non-Goals
- Goals
  - Low-latency market data ingestion and distribution.
  - Robust OMS: order validation, risk checks, routing, lifecycle management for equities and derivatives.
  - Real-time positions, exposures, Greeks (for options), and P&L.
  - Pre-trade and post-trade risk controls with kill switch and circuit breakers.
  - Regulatory compliance: audit trail, surveillance hooks, limits and controls, best-ex handling logic inputs.
  - Strong observability, full auditability, and access controls.
- Non-Goals (Phase 1)
  - Portfolio optimization or algorithmic strategy research tools.
  - Backtesting engine.
  - Exotic derivatives beyond listed options and futures.

## 3. Actors and Roles
- Trader: Places and manages orders, views positions and P&L.
- Risk Manager: Defines limits, monitors exposures, can trigger kill switch.
- Compliance Officer: Reviews activity, runs compliance checks, generates reports.
- Operations: Monitors connectivity, resolves exceptions, manages allocations.
- Admin: Manages users, permissions, and platform configuration.

## 4. In-Scope / Out-of-Scope
- In-Scope: Equities and listed derivatives (futures, options), DMA/broker connectivity, allocations, end-of-day (EOD) processes, reconciliation inputs.
- Out-of-Scope: Fixed income, FX (Phase 2+), OTC derivatives.

## 5. Functional Requirements by Capability

### 5.1 Market Data Ingestion & Distribution
- Support real-time subscription to market data (top-of-book and depth where available), trades, and reference data updates.
- Normalize incoming feeds into a canonical MarketDataTick entity with fields: instrumentId, venue, ts, bid/ask, sizes, lastTradePx/Qty, day stats, status.
- Stream updates to downstream services (risk, pricing, OMS) with sub-100ms end-to-end target from receipt to distribution for top-of-book.
- Resilience: auto-reconnect, gap detection, recovery from sequence gaps.
- Corporate actions and reference data updates trigger instrument refresh events.

### 5.2 Order Management System (OMS)
- Order Entry: market, limit, stop, stop-limit, IOC, FOK, GTC/Day; support replace/amend and cancel.
- Validation: symbol tradability, session status, price collars, lot size, min tick.
- Pre-Trade Risk (before route): notional/quantity thresholds, max order value, fat-finger checks, price banding, credit checks, open-order exposure, position limits, concentration limits.
- Routing: select venue/broker per instrument, account, strategy, or smart-routing rules; support order tags (strategyId, clientOrderId).
- Execution Handling: acknowledge, partial fill, full fill, reject, cancel, cancel-replace; maintain full order state machine and timestamps.
- Amendments and Cancels: track parent/child linkage and audit trail of changes (prev vs new values).
- Derivatives Support: legs for multi-leg options strategies (spread, straddle), futures with expiration/roll rules, margin impact preview.
- Post-Trade: execution capture, allocations to accounts/portfolios, fees and commissions enrichment.

### 5.3 Portfolio, Positions, and Exposures
- Maintain real-time positions per account, portfolio, instrument, venue, and strategy.
- Support long/short, average price, realized/unrealized P&L, quantities on hold (open orders).
- Corporate actions (splits, dividends) adjust positions correctly.
- Aggregations: by account, portfolio, strategy, asset class, venue, trader.
- Derivatives Greeks: delta, gamma, vega, theta for options at instrument and aggregated levels.

### 5.4 Risk Controls
- Limit Types: per-user, per-account, per-portfolio, per-instrument, per-asset class.
- Pre-trade blocks: reject orders breaching limits with reason codes.
- Post-trade monitoring: alert when utilization exceeds thresholds (e.g., 80%, 90%).
- Kill Switch: role-gated ability to cancel open orders and block new orders by scope (user/account/desk/system).
- Circuit Breakers: per-instrument or venue, pausing routing when rapid adverse moves detected.
- Scenario Stress: ability to apply shock scenarios to positions to simulate exposure changes.

### 5.5 Compliance
- Policy Checks: wash trade prevention, restricted list, short-sale rules (locate flag), spoofing patterns (basic heuristics), position and reporting limits.
- Best-Execution Inputs: capture quotes and route decisions for audit; store reasons/tags.
- Surveillance Hooks: emit normalized events to downstream surveillance tools.
- Complete Audit Trail: immutable event log with who/what/when for orders, executions, amendments, cancels, and configuration changes.
- Reporting: exportable activity and exception reports by day, account, trader, venue.

### 5.6 Real-Time P&L and Valuation
- P&L Components: realized, unrealized, fees/commissions, borrow costs, funding.
- Valuation: mark-to-market from latest ticks; options valuation with model inputs (vol, rates) and Greeks.
- Frequency: recompute on every relevant tick, execution, or corporate action.
- Views: instrument, account, portfolio, strategy, and aggregate levels with drill-down.

### 5.7 Connectivity & Integrations
- Venue/Broker Adapters: standardized routing interface; retries, backoff, and circuit-breaking on failures.
- Reference Data: instruments, venues, trading hours, tick sizes, lot sizes maintained as entities and updated via events.
- Import/Export: CSV/JSON import for limits, static data, and initial positions; export reports for compliance and operations.

### 5.8 Alerts, Notifications, and UI Signals
- Threshold-based alerts for risk utilization, connectivity failures, compliance exceptions, and P&L drawdowns.
- User-configurable subscriptions by channel (in-app, email) and severity.

### 5.9 Audit, Observability, and Operations
- Every state change produces an auditable event with correlation IDs and timestamps.
- Health views for data feeds, routing status, backlog, and latency SLOs.
- Operational runbooks embedded as docs; EOD task checklist and status events.

## 6. Event-Driven Workflows (High-Level)
- MarketDataIngestion: Receive tick → Normalize → Publish → Update valuations/Greeks.
- OrderLifecycle: New → Validate → PreTradeRisk → Route → Ack → Partial/Fill/Reject → PostTrade.
- RiskCheck: On order and on schedule → Evaluate limits → Block or allow → Emit utilization metrics.
- ComplianceCheck: On order and post-trade → Evaluate rules → Flag exceptions.
- AllocationWorkflow: Execution → Allocation rules → Create Allocation records → Update positions.
- PositionUpdate: Execution/Cancel/Replace/CorporateAction → Update positions and exposures.
- PnLCalc: Tick/Execution → Revalue → Update P&L aggregates.
- DerivativesLifecycle: Option-specific valuation updates, expiry/assignment, futures roll handling.

## 7. Core Entities (Conceptual)
- Instrument: id, symbol, assetClass, currency, multiplier, optionType, strike, expiry, tickSize, lotSize.
- MarketDataTick: instrumentId, venue, ts, bidPx, bidQty, askPx, askQty, lastPx, lastQty, open, high, low, close.
- Order: clientOrderId, accountId, instrumentId, side, type, qty, price, tif, status, route, tags, parentId.
- Execution: execId, orderId, qty, price, fee, venue, ts.
- Allocation: execId, accountId, qty, price, fee.
- Position: accountId, instrumentId, qty, avgPx, realizedPnL, unrealizedPnL, greeks.
- Portfolio: portfolioId, accounts[], limits[], owner.
- RiskLimit: scope, metric, threshold, soft/hard, window.
- ComplianceRule: id, type, parameters, status.
- Account: accountId, portfolioId, traderId, permissions.
- Venue: id, name, connectivity, tradingHours.
- Strategy: id, name, params, riskBudget.

## 8. Non-Functional Requirements
- Performance: median tick → valuation update < 100ms; median order entry → venue ack < 150ms; sustained order throughput target 500-1,000 msgs/sec.
- Availability: high availability with no single point of failure; graceful degradation under partial outages.
- Durability: all critical events persisted with exactly-once or effectively-once semantics per workflow.
- Security: RBAC, audit logging, least-privilege credentials, encryption in transit/at rest; admin actions require step-up verification.
- Compliance: immutable logs, tamper-evident storage for audit events.
- Scalability: horizontal scaling for ingestion, routing, and computation.
- Data Retention: configurable retention by event type; EOD archival and snapshotting for reconciliation.

## 9. UX Requirements (high-level)
- Dashboards: market watch, order blotter, executions, positions, exposures, P&L with drill-down.
- Filters and search across account, instrument, venue, strategy, trader.
- Real-time indicators for connectivity, risk utilization, and compliance exceptions.

## 10. Acceptance Criteria and KPIs
- End-to-end latency SLOs met for market data and order acknowledgements.
- Accurate, real-time positions and P&L with unit tests and reconciliation checks.
- Pre-trade risk blocks orders breaching limits; audit trail contains evidence of checks.
- Compliance checks flag applicable violations and generate exportable reports.
- Kill switch cancels open orders system-wide within seconds.
- 100% of state transitions recorded with immutable audit events.

## 11. Assumptions & Open Questions
- Assumption: Brokers/venues provide connectivity credentials and conformance details.
- Assumption: Options model inputs (volatility, rates) are supplied via configuration or data feed.
- Open: Which venues/brokers are in scope for Phase 1?
- Open: Specific compliance policies to parameterize (restricted lists, short-sale rules, etc.).
- Open: Precise latency targets per venue and asset class.

## 12. Phasing
- MVP: Equities + futures, core OMS, pre-trade risk, positions, P&L, audit trail, baseline compliance.
- Phase 2: Options Greeks, advanced surveillance hooks, stress scenarios, smart order routing enhancements.

---
Next steps:
1) We will model these as Canvas entities and workflows.  
2) Once you confirm the design, we’ll generate the application.  
3) While the build runs, we can prepare your Cyoda environment and then deploy the app.