# Institutional Trading Platform – Functional Requirements (Draft)

1. Purpose and Scope
- Build an institutional-grade trading platform supporting real-time market data, advanced order management, portfolio tracking, risk controls, regulatory compliance for equities and derivatives, and real-time P&L.
- Support multi-asset coverage for cash equities, equity options, futures, and FX derivatives (spot/forward/swaps) with extension points for additional asset classes.
- Event-driven design: ingest market data, process orders/executions, update positions and P&L, apply risk/compliance checks, and emit auditable events.

2. Users and Roles
- Trader: Enters/amends/cancels orders, views positions and P&L, monitors risk limits and alerts.
- Portfolio Manager: Monitors portfolio exposures, allocations, strategy-level P&L, and risk.
- Risk Officer: Defines and manages risk policies/limits, monitors breaches, approves overrides.
- Compliance Officer: Defines surveillance rules, monitors alerts, investigates exceptions.
- Operations: Monitors integrations, reconciles executions, resolves breaks, manages reference data.
- Administrator: Manages user access, roles, configurations, entitlements.

3. Core Capabilities
3.1 Market Data
- Ingest real-time tick/quote/trade events for instruments from multiple venues.
- Maintain instrument reference data (symbol, ISIN, exchange, tick size, lot size, contract specs, expiries).
- Build and publish normalized market data snapshots (NBBO/top-of-book, OHLC bars) and time-series.
- Corporate actions and instrument lifecycle (splits, dividends, rolls, expirations) with downstream adjustments.

3.2 Order Management System (OMS)
- Create/replace/cancel orders; support parent/child, care/agency, and staged orders.
- Order types: market, limit, stop, stop-limit, peg, iceberg, post-only; time-in-force: DAY, IOC, FOK, GTC.
- Smart routing abstraction (select venue/broker) with configurable routing policies.
- Pre-trade checks: limits, exposure, credit, fat-finger, price collars, instrument eligibility.
- Execution handling: partial fills, multiple fills, average price, commissions/fees, slippage tracking.
- State machine: New → Validated → Routed → PartiallyFilled → Filled → Canceled → Rejected.
- Full audit trail of all state transitions and user/system actions.

3.3 Portfolio, Positions, and Exposure
- Real-time positions by instrument, account, strategy, and portfolio; intraday and end-of-day views.
- Aggregations by sector, venue, currency, maturity bucket, and custom tags.
- Corporate action-aware position adjustments; roll handling for futures and options.
- Exposure metrics: delta, gamma, vega, theta (where applicable); notional and leverage.

3.4 Real-time P&L
- Intraday realized and unrealized P&L by instrument/account/strategy/portfolio.
- P&L drivers: prices, FX rates, commissions/fees, borrow rates, funding costs.
- Snapshot and time-series outputs; explain P&L by factor (price move, carry, fees, FX). 

3.5 Risk Controls
- Limits: per-user, per-account, per-portfolio, per-instrument, and global; units include quantity, notional, participation rate, daily loss, and exposure limits.
- Pre-trade risk gates (blocking), post-trade surveillance (alerting), intraday breach handling (throttle/block).
- Breach workflow: detect → notify → escalate → approve/reject override → audit.

3.6 Regulatory Compliance
- Configurable rules: restricted lists, short-sale locate checks, price collars, wash-trade detection, spoofing patterns, layering, position limits, trade reporting completeness.
- Surveillance workflows: trigger alerts, capture evidence, assign investigator, annotate, resolve/close with reason codes.
- Full audit, lineage, and immutable event logs for orders, executions, and rule evaluations.

3.7 Reporting and Monitoring
- Standard reports: Orders (by status), Executions, Positions, P&L, Limits and Breaches, Compliance Alerts.
- Operational dashboards: data feed health, routing latency, order throughput, backlog metrics.

4. Data Model (high level entities)
- Instrument: id, symbol, exchange, assetClass, tickSize, lotSize, contractSpec, expiry, currency.
- MarketDataTick: instrumentId, ts, bid, ask, bidSize, askSize, last, lastSize, venue.
- Order: id, parentId, accountId, instrumentId, side, qty, filledQty, price, tif, type, status, route, tags.
- Execution: id, orderId, instrumentId, ts, price, qty, venue, fee, commission, liquidityFlag.
- Position: instrumentId, accountId, qty, avgPrice, openQty, realizedPnl, unrealizedPnl, currency.
- Portfolio: id, name, accounts, strategies, limits.
- RiskLimit: id, scope (user/account/portfolio/instrument/global), metric, threshold, window, action.
- ComplianceRule: id, name, scope, parameters, severity, enabled.
- PnLSnapshot: scope (instrument/account/strategy/portfolio), ts, realized, unrealized, fees, fxImpact, notes.
- ReferenceDataEvent: type (corporateAction, instrumentUpdate), payload.

5. Events and Workflows (to be modeled in Canvas)
5.1 Market Data Ingestion
- Trigger: External tick/quote/trade events.
- Process: Normalize → Validate → Publish tick event → Update snapshot/bar → Notify downstream.
- Outputs: Normalized MarketDataTick, SnapshotUpdated, BarClosed events.

5.2 Order Lifecycle
- Trigger: Create/Replace/Cancel order request.
- Process: Pre-trade risk → Compliance → Routing → Acknowledge → Execution updates → Completion.
- Outputs: OrderAccepted/Rejected, OrderRouted, ExecutionReceived, OrderFilled/PartiallyFilled, OrderCanceled.

5.3 Pre-Trade Risk Check
- Trigger: New/Amended order.
- Checks: quantity/notional, price collars, exposure by account/portfolio, fat finger, restricted instruments.
- Actions: Block, throttle, or approve. Emit LimitBreached/LimitApproved events.

5.4 Compliance Evaluation
- Trigger: New/Amended order and Execution events.
- Rules: restricted lists, wash trades, spoofing patterns, position limits, short-sale locate.
- Actions: Alert, hold, or allow. Emit ComplianceAlert/ComplianceCleared events.

5.5 Execution Processing
- Trigger: Execution/Fill events from venues.
- Process: Match to order, update average price and filledQty, compute fees/commissions, update realized P&L.
- Outputs: ExecutionProcessed, OrderStateUpdated, RealizedPnlUpdated.

5.6 Positions and P&L
- Trigger: ExecutionProcessed, MarketDataTick, CorporateAction.
- Process: Revalue positions, compute unrealized P&L, aggregate by scopes, publish snapshots and timeseries.
- Outputs: PositionUpdated, PnLSnapshotGenerated.

5.7 Corporate Actions and Instrument Lifecycle
- Trigger: ReferenceDataEvent.
- Process: Adjust positions and historical P&L; notify OMS and reporting.
- Outputs: CorporateActionApplied, PositionAdjusted.

6. Business Rules
- Order aging and auto-cancel policies; resubmission limits; amend rules for partially filled orders.
- Venue routing rules by instrument/liquidity/fees; scheduled batch re-routing.
- Risk breach escalation paths with timeouts and approval hierarchies.
- Compliance severity levels with mandatory review timeframes and retention.

7. Non-Functional Requirements
- Latency: end-to-end order acceptance to route ACK under defined thresholds; tick-to-snapshot update targets.
- Throughput: sustained orders/sec and market ticks/sec with burst handling.
- Reliability: high availability and graceful degradation under feed or venue outages.
- Security: role-based access control, least privilege, encryption in transit/at rest.
- Auditability: immutable logs for all decisions, full lineage from input to outputs.
- Observability: metrics, logs, alerts for all critical workflows and integrations.
- Data retention: configurable per artifact; archival of historical ticks and P&L.
- Configurability: rules, limits, and routing policies adjustable without redeploy.

8. Acceptance Criteria (MVP)
- Ingest market data for at least equities and one derivatives class; produce normalized ticks and snapshots.
- Submit basic orders (market/limit) and manage full lifecycle with execution updates.
- Enforce pre-trade risk checks with configurable limits and generate breach events.
- Evaluate a core set of compliance rules and produce actionable alerts.
- Maintain real-time positions and generate P&L snapshots (realized and unrealized) with time-series.
- Provide reports for orders, executions, positions, P&L, risk breaches, and compliance alerts.
- End-to-end audit trail for key workflows and user actions.

9. Open Questions
- Exact list of venues/brokers and routing policies.
- Detailed derivatives coverage (greeks computation scope, margining approach, exercise/assignment flow).
- Corporate actions data source and timing SLAs.
- Currency conversions and multi-currency valuation specifics.
- Specific regulatory jurisdictions and reporting obligations.

Notes
- This draft will drive the Canvas design of entities and workflows. We will refine sections as we clarify open questions and finalize the MVP scope.