# Institutional Trading Platform – Functional Requirements

## 1. Purpose
Deliver an institutional-grade trading platform on Cyoda that supports real-time market data, advanced order and execution management, comprehensive portfolio tracking, rigorous risk controls, regulatory compliance for equities and derivatives, and real-time P&L calculations.

## 2. Scope
- Asset classes: Equities and exchange-traded derivatives (index/stock futures and options).
- Core modules: Market Data, Order & Execution Management, Portfolio & Positions, Risk Controls, Compliance, Real-time P&L, Fees/Costs.
- Interfaces: UI dashboards and programmatic APIs for order entry, monitoring, and reporting.

Out of scope (initial release): OTC derivatives, portfolio optimization, OMS–EMS vendor integrations, historical tick replay.

## 3. Stakeholders & User Roles
- Trader: Place/modify/cancel orders, view executions, P&L, risk limits.
- Sales Trader: Manage client orders, block trades, allocations.
- Risk Officer: Configure and monitor risk limits, approve overrides, receive alerts.
- Compliance Officer: Maintain rules, review alerts, approve restricted instruments/exceptions.
- Portfolio Manager: Monitor positions, exposures, P&L, performance attribution.
- Operations: Reconciliations, corporate actions processing, EOD checks.
- System Admin: User/RBAC management, configuration, environment oversight.
- API Client: Programmatic access for order entry and data retrieval.

## 4. High-level Capabilities
1) Market Data
- Subscribe to top-of-book, depth, and trades for supported instruments.
- Normalize updates into a canonical entity model; handle trading sessions and halts.
- Maintain instrument reference and corporate actions for accurate positions and P&L.

2) Order & Execution Management
- Support market, limit, stop, stop-limit, IOC, FOK, GTC/GTD; parent/child and slicing.
- Routing abstraction to multiple venues; receive and correlate execution reports.
- Robust lifecycle: New → Acknowledged → PartiallyFilled → Filled → Canceled/Rejected.
- Amend/cancel with versioning, idempotency, and duplicate detection.

3) Portfolio & Positions
- Real-time positions by account, instrument, venue, and strategy; open/close tracking.
- Cash balances and corporate action effects (splits, dividends) reflected in positions.
- Multi-currency support with FX rates for exposure and P&L translation.

4) Risk Controls
- Pre-trade: price collars, max order qty/notional, position and exposure limits, credit checks, restricted instruments/lists, max child orders, fat-finger checks.
- Intraday: real-time exposure and limit utilization; automatic block and alerting.
- Override workflow requiring dual-approval with full audit trail.

5) Compliance
- Rules-based checks: restricted list, concentration thresholds, wash/dup order patterns, short-sale locates flagging, and venue eligibility.
- Surveillance alerts with triage, status, assignment, and resolution notes.
- Auditability: immutable event logs, time-stamped to millisecond precision.

6) Real-time P&L
- Per-instrument, per-account, per-portfolio P&L snapshots with realized/unrealized.
- Mark-to-market using latest quotes/trades; configurable mid/last/close selection.
- Attribution: price move, FX, fees/commissions; aggregation by strategy/desk.

7) Fees & Costs
- Commission schedules, exchange/clearing fees, taxes; apply at execution and include in P&L.

## 5. Detailed Functional Requirements
A) Market Data
- Instrument master with identifiers, tick size, lot size, trading calendar, currency.
- Subscriptions per user/strategy; throttling and entitlement checks.
- Event normalization: QuoteUpdate, TradePrint, TradingStatus, CorporateAction.
- Data quality: gap detection, stale feed detection, and self-healing resubscription.

B) Order Management
- Order entry API/UI with validation of instrument tradability and session status.
- Supported fields: side, qty, price, tif, account, strategy, venue hints, algo params.
- Amend: preserve audit trail with prior values and effective timestamps.
- Cancel: immediate request with success/failure feedback; partial fills preserved.
- Execution handling: partials, average price, remaining qty, fees; real-time updates.
- Parent/child orchestration for slicing; configurable child sizing and intervals.

C) Routing & Venue Abstraction
- Venue selection rules (best price, preferred venue, dark/light preference).
- Failover: re-route on venue rejection or timeout with clear audit trail.

D) Risk Controls
- Configurable limit types: per-instrument, per-sector, per-account, per-portfolio.
- Calculation windows: intraday rolling and daily hard limits.
- Breach handling: block order, alert risk officer, optional escalation workflow.

E) Compliance & Surveillance
- Pre-trade compliance checks in the order path with synchronous verdicts.
- Post-trade surveillance events for pattern detection; alert queue with SLA.
- Evidence capture: complete message payloads, user context, and decisions.

F) Portfolio & Positions
- Position updates triggered by executions, corporate actions, and adjustments.
- Support long/short, opening/closing tags; FIFO and configurable lot selection.
- Corporate actions engine: apply splits, dividends, options expiry/assignment.

G) Real-time P&L
- Formulas: 
  - Unrealized = (MarkPrice - CostBasis) * Quantity (adjusted for contract size).
  - Realized = Sum(execution P&L - fees) by closed lots.
- Frequency: recalculation on any relevant market or execution event; snapshot every N seconds configurable.
- Hierarchies: instrument → account → strategy → portfolio → firm.

H) Reporting & Dashboards
- Trader blotter: orders, fills, status, rejections, live P&L.
- Risk dashboard: limits, utilization, breaches, exposures, alerts.
- Compliance dashboard: rules, alerts, statuses, audit timelines.
- Portfolio view: positions, cash, exposures, attribution, performance.

I) APIs & Integrations
- Order API: submit/amend/cancel, query order/execution status, pagination, filters.
- Market Data API: subscribe/unsubscribe, snapshot endpoints.
- Data export: positions, P&L, and executions as downloadable reports.

## 6. Security & Access Control
- Role-based access control with least-privilege defaults; environment-level segregation.
- Sensitive actions (limit changes, overrides) require elevated roles and approvals.
- Full audit trail of user actions and system decisions.

## 7. Non-Functional Requirements
- Latency targets: 
  - Market data normalization to availability: p50 ≤ 50 ms, p99 ≤ 200 ms.
  - Order ack round-trip (platform side): p50 ≤ 75 ms, p99 ≤ 300 ms.
- Throughput: sustain 5k market updates/sec and 200 order msgs/sec initially; horizontally scalable.
- Availability: ≥ 99.9% monthly for trading hours; graceful degradation outside.
- Consistency: event-driven processing with idempotent handlers; exactly-once effects at entity boundary.
- Observability: task and workflow health, error rates, and alerting surfaced in platform dashboards.
- Data retention: audit logs ≥ 7 years; market data events ≥ 90 days; configurable.

## 8. Data Model (Conceptual Entities)
- Instrument, Quote, TradePrint, TradingStatus, CorporateAction
- Order, ChildOrder, ExecutionReport, VenueRoute
- Account, Portfolio, Position, CashBalance
- RiskLimit, RiskBreach, RiskOverride
- ComplianceRule, ComplianceAlert, Approval
- PnlSnapshot, FeeSchedule, Commission

## 9. Key Event Workflows (to be modeled in Canvas)
- MarketDataIngestion: normalize Quote/Trade/Status events.
- OrderLifecycle: validate → risk/compliance checks → route → ack/fill/cancel.
- RiskCheck: pre-trade synchronous checks; async exposure updates.
- ComplianceCheck: rule evaluation; alert generation/triage.
- PositionUpdate: update positions on execution and corporate actions.
- PnlCalculation: real-time mark and periodic snapshots.

## 10. Acceptance Criteria (Examples)
- Orders: submit/ack/cancel/amend produce correct state transitions and audit logs.
- Risk: orders violating configured limits are blocked; overrides require dual-approval.
- Compliance: rules execute pre-trade; alerts generated post-trade with complete evidence.
- Portfolio: positions update within 1 second of executions; corporate actions correctly applied.
- P&L: snapshots reflect latest market data within 500 ms of updates.
- APIs: order query returns consistent state with pagination and filters.

## 11. Operational Considerations
- Environment separation: dev, staging, prod; controlled promotion of configs and rules.
- Configuration management: rule/limit versioning with effective date/times.
- Backup & recovery: periodic snapshots of critical entities and configurations.

## 12. Glossary
- P&L: Profit and Loss; Mark-to-Market: valuation using latest available market price.
- Parent/Child Orders: orchestration where a parent order spawns multiple slices.
- Exposure: aggregation of risk across instruments/portfolios.

---
This document defines the initial design. We will refine entities and workflows in Canvas, then generate the application. 