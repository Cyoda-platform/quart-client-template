# Institutional Trading Platform — Functional Requirements (First Pass)

## 1. Overview
Build an institutional-grade trading platform supporting real-time market data ingestion, advanced order management, portfolio tracking, risk controls, regulatory compliance for equities and derivatives, and real-time P&L calculations. The system will be event-driven and designed for high throughput, low latency, and strong auditability.

## 2. Objectives
- Provide a unified platform for trading across equities and listed derivatives.
- Deliver real-time market data and analytics to power decision-making.
- Execute and manage complex order workflows with rich state tracking and risk gates.
- Maintain comprehensive portfolio and position views with real-time P&L (realized/unrealized). 
- Enforce pre-trade and post-trade risk and compliance controls.
- Offer complete audit trails and compliance reporting.

## 3. In Scope
- Market data ingestion (quotes, trades, reference data, corporate actions)
- Order Management System (OMS) with full order lifecycle and child-order routing
- Risk controls (pre-trade checks, exposure limits, kill-switches)
- Regulatory compliance (surveillance hooks, trade capture/audit, restricted lists)
- Portfolio/positions with multi-asset support (equities, futures, options)
- Real-time P&L: tick-by-tick revaluation, intraday and end-of-day
- Event logging, user permissions, and comprehensive auditability

## 4. Out of Scope (Initial Release)
- Exotic derivatives and OTC lifecycle specifics
- Portfolio optimization and advanced analytics beyond basic Greeks for listed options
- Historical backtesting framework

## 5. Users & Roles
- Trader: Creates, modifies, and cancels orders; views positions/P&L.
- Risk Officer: Manages limits, approves overrides, monitors exposure.
- Compliance Officer: Manages restricted lists, monitors alerts, audits activity.
- Operations: Reconciles trades, handles allocations, investigates breaks.
- Admin: Manages users, roles, configuration, and reference data.

## 6. Key Functional Modules

### 6.1 Market Data
- Ingest real-time price data (Level 1 bid/ask/last, volume), trades, and reference data.
- Normalize to common instrument model (symbol, exchange/venue, currency, contract specs for derivatives).
- Validate and timestamp all ticks; handle out-of-order and late data.
- Publish normalized market data events for downstream consumers (risk, P&L, OMS).

### 6.2 Order Management System (OMS)
- Captures parent orders with instructions (side, quantity, time-in-force, price, algo flags).
- Supports child-order creation and routing, partial fills, and amendments.
- Order states: New → PendingRisk → RiskApproved/Rejected → Working → PartiallyFilled → Filled → CancelPending → Cancelled → Rejected.
- Supports market/limit/stop/stop-limit, IOC/FOK/GTD, and basic algo flags.
- Broker/venue routing abstraction.
- SLA: Accept orders and transition to PendingRisk within 20 ms (target) from submission.

### 6.3 Risk Controls
- Pre-trade checks: max order size, price collars, fat-finger checks, credit/exposure by account/strategy, restricted instruments.
- Intraday exposure updates on every fill and price tick (mark-to-market).
- Kill-switch per account/desk with immediate effect; bulk cancel of working orders when invoked.
- Limit configuration versioned and auditable; override workflow with approvals and reason codes.

### 6.4 Regulatory Compliance
- Maintain restricted lists and watchlists; block orders violating these rules.
- Surveillance hooks: flag patterns (e.g., layering/spoofing signals) for review.
- Trade capture with immutable audit trail: all submissions, state transitions, fills, and cancellations.
- Data retention policies and export for reporting; searchable audit queries.

### 6.5 Portfolio & Positions
- Positions tracked by account/strategy/instrument (including derivatives and underlying linkage).
- Real-time position updates on fills, corporate actions, and lifecycle events.
- Valuation supports equities, futures, and options (basic Greeks for options: delta, gamma, vega, theta; configurable models).
- Aggregations: by instrument, sector, account, desk, portfolio; multi-currency with FX conversion.

### 6.6 Real-time P&L
- Intraday unrealized P&L recalculated on each price tick; realized P&L on fills.
- P&L components: price P&L, FX P&L, fees/commissions, financing/carry (configurable).
- Snapshots at intervals and on-demand; end-of-day closing snapshots.
- Drill-down from portfolio → instrument → execution level.

## 7. Core Entities (first pass)
- Instrument: id, symbol, type (Equity/Future/Option), exchange, currency, tickSize, contractSpecs (expiry, strike, callPut, multiplier).
- MarketDataTick: instrumentId, ts, bid, ask, last, volume, venue.
- Order: id, parentId, accountId, instrumentId, side, orderType, tif, qty, price, algoFlags, status, timestamps.
- Execution/Fill: id, orderId, qty, price, fees, venue, ts, tradeId.
- Position: accountId, instrumentId, qty, avgPrice, realizedPnL, unrealizedPnL, greeks, lastTs.
- Portfolio: id, accounts, riskLimits, baseCurrency, valuationPolicy.
- RiskLimit: id, scope (account/desk), type (maxOrderQty, exposure, priceCollar, restrictedList), threshold, currency, effectiveDates.
- ComplianceRule: id, type, conditions, action (block/warn/allow), effectiveDates.
- CorporateAction: instrumentId, type (split/dividend/roll), params, effectiveDate.
- User: id, role, permissions, status.

## 8. Event Streams (examples)
- market-data.ingested
- order.submitted, order.amended, order.cancel.requested
- order.risk.pending, order.risk.approved, order.risk.rejected
- order.routed, order.working, order.partially-filled, order.filled, order.cancelled, order.rejected
- execution.reported
- position.updated, portfolio.valued
- risk.limit.updated, risk.killswitch.activated
- compliance.alert.raised, compliance.rule.updated
- pnl.updated, eod.snapshot.completed

## 9. Primary Workflows (first pass)
1) MarketDataIngestion
   - Validate → Normalize → Publish → Update P&L and Risk caches.
2) OrderLifecycle
   - Submit → PendingRisk → RiskDecision → Route → Working → Partial/Fill → Completion → Post-trade capture.
3) PreTradeRiskCheck
   - Evaluate limits (size, price collar, exposure, restricted list) → Approve/Reject → Log audit.
4) PostTradeRiskAndSurveillance
   - Monitor fills/positions for breaches and patterns → Alerts → Actions (notify/block).
5) RealTimePnLCalculation
   - On tick or fill: revalue positions, compute Greeks/P&L → Publish snapshots.
6) PortfolioValuation
   - Aggregate positions → FX conversion → Portfolio metrics → Snapshots.
7) CorporateActionProcessing
   - Apply events to positions (splits, dividends, rolls) → Adjust positions and cost basis.

## 10. Business Rules (examples)
- Price collar: limit orders must be within X% of reference price; configurable per instrument/venue.
- Max order quantity by account/instrument class; reject if exceeded.
- Exposure: projected exposure after order ≤ limit; includes delta-adjusted for options.
- Restricted instruments: block orders when instrument on restricted list.
- Kill-switch effect: cancel all working orders for the scope and block new orders until reset.

## 11. Non-Functional Requirements
- Latency: pre-trade risk decision median < 20 ms; 99th < 100 ms.
- Throughput: handle 50k market-data ticks/sec and 5k order events/sec initially; horizontally scalable.
- Availability: design for high availability; no single-point-of-failure in critical paths.
- Reliability: at-least-once event processing; idempotent handlers; exactly-once semantics where feasible in state updates.
- Security: role-based access control; data encryption in transit and at rest; fine-grained permissions by role.
- Observability: metrics, logs, and traces for all workflows; alerting on SLO breaches.
- Auditability: immutable audit log for orders, risk decisions, and compliance actions; tamper-evident storage.
- Configurability: runtime configuration for limits, price collars, valuation policies, and risk parameters.

## 12. Interfaces (first pass)
- Order API: submit/amend/cancel, query order status, get executions.
- Market Data API: subscribe to normalized price streams and snapshots.
- Portfolio API: positions by account/strategy, portfolio metrics, P&L snapshots.
- Admin API: manage users, roles, risk limits, compliance rules, and reference data.

## 13. Data Retention & Governance
- Retain trade/Order/Audit data per policy; configurable retention windows.
- Export interfaces for compliance reporting and archival.
- Access controls and approval workflows for sensitive data.

## 14. Acceptance Criteria (initial)
- Orders are blocked when any configured pre-trade limit is violated and the decision/audit reason is recorded.
- Market data ticks update unrealized P&L within 100 ms end-to-end for impacted instruments.
- Positions and P&L reconcile with executions intraday and at end of day.
- Kill-switch cancels all working orders within the defined scope and prevents new orders instantly.
- All order state transitions, risk decisions, and compliance actions are captured in the audit trail.

## 15. Open Questions
- Specific exchanges/venues and data sources to prioritize for phase 1?
- Exact valuation model preferences for options (e.g., param sets) and FX sources for multi-currency P&L?
- Required retention periods by data type and region?
- Required alerting thresholds for surveillance and SLOs?

---
This is a first-pass specification. We will refine entities and workflows in Canvas, then generate the full Cyoda application. Once you confirm, we’ll proceed to build and prepare the environment for deployment.