# Institutional Trading Platform – Functional Requirements

## 1. Purpose and Scope
Design and deliver an institutional-grade trading platform supporting real-time market data ingestion, advanced order management, portfolio and risk, regulatory compliance for equities and derivatives, and real-time P&L. The platform will be built as an event-driven Cyoda application with clear entities, workflows, and policies that can be evolved iteratively in Canvas.

## 2. Actors and Roles
- Trader: creates and manages orders, monitors fills and P&L.
- Portfolio Manager: defines strategies, monitors exposures and performance.
- Risk Manager: sets limits and policies, monitors breaches.
- Compliance Officer: manages rules, reviews alerts and reporting obligations.
- Operations: allocation, breaks resolution, end-of-day (EOD) processes.
- Administrator: user management, entitlements, configuration.
- External: Market Data Provider, Execution Venues, Clearing/Broker.

## 3. Key Capabilities
1) Real-time Market Data
- Ingest tick-by-tick quotes/trades from multiple sources.
- Normalize into unified Instrument and MarketDataTick events.
- Maintain last price, bid/ask, book depth snapshot, and trading status.

2) Advanced Order Management (OMS)
- Order lifecycle: New → Risk Checks → Routing → Venue Ack → Partial/Full Fill → Amend/Cancel → Complete.
- Support order types: Market, Limit, Stop/Stop-Limit, Iceberg, Pegged; time-in-force: DAY, IOC, FOK, GTC.
- Routing: smart order routing across multiple venues with preferences and cost/latency metrics.
- Amend/Cancel with versioned audit trail. Child order creation for slicing.

3) Portfolio & Positions
- Real-time positions by account, instrument, and strategy.
- Corporate actions adjustments (splits, dividends) reflected in positions and P&L.
- Allocations from executions to accounts/strategies.

4) Risk Controls
- Pre-trade: fat-finger checks (qty/notional), price bands, max participation, credit and exposure limits, restricted instruments/venues.
- Post-trade: concentration and global exposure checks; intraday limit recalculation.
- Breach handling: block, warn, require approval; event capture and audit.

5) Compliance
- Restricted lists (instruments, issuers), watch lists, blackout windows.
- Pattern detection rules (cross/ wash-like behavior, layering/spoofing signals via event patterns where applicable).
- Record-keeping, audit trails, exception workflows, reporting triggers.

6) Real-time P&L
- Intraday and end-of-day P&L (realized/unrealized), fees and commissions.
- For derivatives: Greeks estimates and margin impact using configurable models.
- P&L impact on ticks, fills, and corporate actions.

## 4. Domain Entities (logical model)
- Instrument: id, symbol, assetClass (Equity/Future/Option), exchange, currency, multiplier, tickSize, contractDates (for derivatives), underlyingId.
- MarketDataTick: instrumentId, ts, type (QUOTE/TRADE), bid, ask, bidSize, askSize, last, lastSize, bookDepth (optional), tradeCondition.
- Order: id, parentId (for child orders), clientOrderId, accountId, strategyId, instrumentId, side (BUY/SELL), type, tif, qty, price, status, routedVenueIds, creationTs, lastUpdateTs, attributes (iceberg, peg, discretionary, routing hints).
- Execution: id, orderId, venueId, instrumentId, execType (ACK/FILL/CANCEL/REJECT), qty, price, fee, liquidityFlag, tradeTs.
- Allocation: id, executionId, accountId, qty, price, fee.
- Position: id, accountId, instrumentId, qty, avgPrice, realizedPnL, unrealizedPnL, lastTs.
- Portfolio: id, name, accounts[], strategies[], exposures (by assetClass, sector, currency), limits[]
- RiskLimit: id, scope (account/portfolio/strategy/global), metric (notional, qty, VaR, concentration), threshold, mode (BLOCK/WARN/APPROVE), window.
- ComplianceRule: id, name, type (restrictedList, pattern, blackout), parameters, active.
- Venue: id, name, region, fees, capabilities (orderTypes, tif, assetClasses), connectionStatus.
- Strategy: id, name, owner, description, params.
- PnLMetric: id, accountId/portfolioId, instrumentId, realized, unrealized, fees, greeks {delta, gamma, vega, theta}, ts.

## 5. Events and Topics
- MarketDataTickReceived
- InstrumentUpdated
- OrderSubmitted
- OrderRiskApproved / OrderRiskRejected
- OrderRouted
- VenueAckReceived
- ExecutionReportReceived (PartialFill/FullFill/Cancel/Reject)
- AllocationBooked
- PositionUpdated
- PnLUpdated
- RiskLimitBreached
- ComplianceAlertRaised
- EndOfDayRolled
Each event includes metadata: eventId, ts, userId or systemId, correlationId (orderId where applicable), source.

## 6. Core Workflows
A) Market Data Ingestion & Normalization
- Trigger: MarketDataTickReceived
- Steps: validate instrument → normalize units → update last/bbo/book snapshot → emit PnL recalculation for impacted positions → optional compliance/risk hooks.

B) Order Lifecycle
- Trigger: OrderSubmitted
- Steps: validate & enrich → pre-trade risk checks → compliance checks → route to venues (can spawn child orders) → handle acks/fills → update order state → book allocations → update positions → emit PnLUpdated.

C) Pre-Trade Risk Controls
- Trigger: OrderSubmitted/Amended
- Checks: qty/notional, price bands, participation caps, credit/exposure, restricted instruments/venues.
- Outcome: Approved or Rejected (with reason); or ApprovalRequired event for overrides.

D) Compliance Surveillance
- Trigger: Order/Execution/MarketData patterns
- Rules: restricted lists, blackout, pattern heuristics.
- Outcome: ComplianceAlertRaised with severity and action (block/warn/escalate).

E) Positions & Portfolio Update
- Trigger: AllocationBooked/ExecutionReportReceived
- Steps: update position quantities, average price, realized P&L; recalc exposures; update portfolio aggregates.

F) Real-time P&L
- Trigger: MarketDataTickReceived/ExecutionReportReceived
- Steps: unrealized P&L on price ticks, realized P&L on fills; include fees and commissions; derivatives: greeks roll-up to account/portfolio.

G) End-of-Day
- Trigger: EndOfDayRolled
- Steps: finalize valuations, roll corporate actions, archive audit, reset intraday metrics.

## 7. State Models
- Order.status: NEW → PENDING_RISK → RISK_REJECTED | PENDING_COMPLIANCE → COMPLIANCE_REJECTED | ROUTING → PARTIALLY_FILLED → FILLED | CANCELED | REJECTED.
- Execution.execType: ACK, PARTIAL_FILL, FILL, CANCEL, REJECT.
- Position lifecycle: updated on allocations/fills; valued continuously on ticks.

## 8. Risk & Compliance Policies
- Limit types: per-order qty/notional, per-instrument exposure, per-account credit, per-portfolio concentration, firm-wide exposure.
- Actions: BLOCK, WARN, REQUIRE_APPROVAL; all actions must be auditable with rationale.
- Compliance rules: restricted instruments/issuers, blackout windows, alerts on suspicious patterns; rule parameters managed by Compliance Officer.

## 9. Non-Functional Requirements
- Latency: sub-second reaction to market ticks and order updates; low-latency event handling for routing and fills.
- Throughput: scale to millions of ticks/day and thousands of orders/day.
- Reliability: exactly-once or idempotent processing semantics for critical events; durable audit trails.
- Observability: task status, metrics, and traceability across workflows.
- Security & Entitlements: role-based access, per-entity ACLs, full audit logging.

## 10. APIs and UI
- UI views: Market data monitor, Order ticket, Order/Execution blotter, Positions & P&L, Risk dashboard, Compliance alerts.
- APIs: order entry/amend/cancel, market data subscription, portfolio and risk queries.

## 11. Acceptance Criteria (sample)
- Market ticks update P&L for impacted positions within 1s.
- Pre-trade risk prevents orders breaching configured limits; overrides require approval and audit.
- Compliance rules generate alerts with severity and traceable event history.
- Positions update within 1s of allocations; portfolio exposures recalc and persist.
- End-of-day rolls update realized P&L and archives intraday events.

## 12. Open Questions
- Venue connectivity specifics, fee models, and routing policies.
- Derivatives models and parameters for Greeks and margin.
- Reporting destinations and formats for compliance and operations.

---
Next steps in Canvas:
- Review and refine entities and workflows above.
- Confirm risk and compliance rules and thresholds.
- When ready, generate the full application from this design and proceed to environment deployment.