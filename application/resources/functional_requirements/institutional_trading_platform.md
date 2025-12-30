# Institutional Trading Platform — Functional Requirements

## 1. Overview
- Purpose: Build an institutional-grade trading platform supporting real-time market data, advanced order management, comprehensive portfolio tracking, pre/post-trade risk controls, regulatory compliance across equities and derivatives, and real-time P&L.
- Users: Traders, Portfolio Managers, Risk Officers, Compliance Officers, Operations, Admins.
- Asset Classes: Equities (cash), Listed derivatives (futures/options); extensible to others.

## 2. Goals and Scope
- Real-time ingestion and normalization of market data (quotes, trades, depth, reference data).
- Advanced OMS: order capture, validation, risk checks, routing, execution handling, allocations.
- Real-time portfolio and position management with intraday updates.
- Risk controls: credit/exposure/fat-finger/concentration/price collars; circuit-breakers.
- Compliance: surveillance rules, restricted lists, approvals, audit trails, retention.
- Real-time P&L: realized/unrealized, mark-to-market using mid/last/close, fee/slippage modeling.
- Non-functional: Low-latency paths, high throughput, resiliency, observability, RBAC, data retention.

Out of scope (initial cut): Portfolio optimization, strategy backtesting, clearing/settlement.

## 3. Actors and Roles
- Trader: Places/edits/cancels orders, views market/positions/P&L.
- Portfolio Manager: Reviews exposures, approves blocks, monitors P&L.
- Risk Officer: Configures limits, monitors breaches, approves overrides.
- Compliance Officer: Manages surveillance rules, restricted lists, approvals, audits.
- Operations: Allocations, breaks management, end-of-day controls.
- Admin: User/role management, configuration, environment controls.

## 4. Core Entities (initial)
- Instrument: {symbol, isin, venue, assetClass, tickSize, contractSpec, multiplier, currency}
- MarketDataTick: {instrumentId, ts, bid, ask, last, bsz, asz, vol, bookLevels}
- ReferenceData: {instrumentId, status, close, corporateActions}
- Order: {orderId, clientOrderId, accountId, instrumentId, side, qty, type, tif, limitPrice, stopPrice, routingVenue, strategy, parentOrderId, status, timestamps}
- ChildOrder: like Order with parent linkage
- ExecutionReport: {execId, orderId, instrumentId, price, qty, liquidityFlag, fees, ts, venue}
- Allocation: {allocationId, blockOrderId, accountId, qty, price, ts}
- Position: {accountId, instrumentId, netQty, longQty, shortQty, avgPrice, openPnL, realizedPnL}
- Portfolio: {portfolioId, accounts[], exposures, greeks}
- RiskLimit: {limitId, scope(account/portfolio/global), type(notional, quantity, value-at-risk proxy, concentration), threshold, window, currency}
- ComplianceRule: {ruleId, name, type(restrictedList, preClear, maxOrderSize, washTrade, crossTrade), params}
- PnLEntry: {accountId, instrumentId, ts, realized, unrealized, fees, slippage, total}
- User: {userId, role, permissions, desks}
- AuditEvent: {eventId, actor, action, entityType, entityId, ts, payloadHash}

## 5. Market Data Requirements
- Feeds: Top-of-book, full depth (configurable), trades, reference updates.
- Latency targets: ingest-to-publish p50 ≤ 50ms, p99 ≤ 200ms for quote/last, depth optional.
- Normalization: standardize symbols, venues, units; enrich with reference data.
- Throttling/Downsampling: per-instrument and global; burst protection; backpressure.
- Reliability: replay on reconnect, gap detection, sequence alignment, late data handling.
- Derived metrics: NBBO-like best bid/ask, mid, spreads, rolling VWAP/TWAP (configurable windows).

## 6. Order Management (OMS)
- Order Types: market, limit, stop, stop-limit, peg (mid/primary/market), IOC, FOK, GTC, DAY.
- Lifecycle: New → Validated → RiskChecked → Routed → PartiallyFilled/Filled → Cancelled/Rejected.
- Amend/Cancel: Replace (price/qty), cancel request/ack flow with state consistency.
- Routing: venue selection by rules (instrument/venue availability, liquidity, cost, limit types).
- Pre-trade checks: price collars, max order size, fat-finger (notional/qty), credit and exposure by account/portfolio, restricted instruments, duplicates.
- Post-trade checks: fill reconciliation, slippage vs benchmarks, fee capture, trade breaks.
- Block/Child: parent-child slicing, POV/time-slice, participation caps, residual cleanup.
- Idempotency: clientOrderId uniqueness; safe retries for at-least-once delivery.
- Sequencing: strict ordering per orderId; causal ordering for parent/child chains.

## 7. Portfolio, Positions, and P&L
- Positions: real-time updates on executions and corporate actions; intraday snapshots.
- Valuations: mark-to-market by policy (mid/last/close, per asset class); FX conversion rules.
- P&L: real-time realized/unrealized; include fees/commissions; configurable slippage model.
- Aggregations: by instrument, account, portfolio, desk, strategy; drill-down from totals.
- Corporate Actions: splits/dividends/options rolls; adjustment rules and effective dates.

## 8. Risk Management
- Limits: per account/portfolio/global on notional, qty, delta-equivalent for derivatives, concentration by instrument/sector.
- Breach handling: warn/block; escalation to Risk Officer; override workflow with audit.
- Intraday risk: rolling windows; exposure calculators; what-if checks before send.
- Circuit breakers: kill-switch per account/desk/instrument; auto-halt on cascading rejections.
- Scenario hooks: stress shocks on price/vol for intra-day inspection (non-blocking).

## 9. Compliance and Audit
- Pre-trade: restricted lists, approval-required instruments, max order size by user/instrument.
- Post-trade: cross-trade/wash-trade detection, spoofing/ layering heuristics, pattern alerts.
- Approvals: workflow for risk/compliance sign-off on exceptions with full audit.
- Audit Trail: immutable event log of all actions and decisions with timestamps and actor.
- Record Retention: configurable retention windows by entity type and region.

## 10. Real-time Processing and Workflows (Event-driven)
- MarketDataIngest: TickIngested → Normalize → PublishQuote/Trade → DerivedMetricsUpdated.
- ValidateOrder: OrderReceived → SchemaValidation → Enrich → Validated|Rejected.
- RiskCheck: Validated → RiskEvaluated → RiskPassed|RiskFailed(Reason).
- ComplianceCheck: RiskPassed → ComplianceEvaluated → CompliancePassed|ComplianceFailed.
- RouteOrder: CompliancePassed → VenueSelected → OrderRouted → AckReceived|RouteFailed.
- ExecutionHandling: FillOrAck → UpdateOrderState → UpdatePosition → UpdatePnL → Notify.
- Allocation: BlockFilled → SuggestAllocations → Approve → Allocate → Booked.
- PositionRollup: PositionDelta → AggregatePortfolio → PublishExposures.
- PnLUpdate: Tick or Execution → Revalue → PublishPnL.
- BreachHandling: Risk/Compliance Breach → Alert → (Optional) ApproveOverride → Proceed/Halt.
- EndOfDay: ClosePrices → Final Valuation → Reports → Archive.

## 11. APIs and Interfaces
- Ingestion: market data events; order submission/amend/cancel; allocations input.
- Subscriptions: quotes, trades, order state, executions, positions, P&L, breaches, alerts.
- Admin: limits, rules, lists, user/role management, configuration.

## 12. Non-Functional Requirements
- Performance: ingest to publish p50 ≤ 50ms (quotes/trades), order path validation+risk+routing p95 ≤ 150ms under normal load.
- Throughput: 50k ticks/sec sustained; 1k orders/sec; scalable horizontally.
- Availability: target ≥ 99.9%; graceful degradation on partial service loss.
- Resilience: retries with backoff; idempotent processors; exactly-once effects for state changes.
- Observability: metrics, logs, traces for workflows, processors, and queues; alerting on SLO breaches.
- Security: RBAC, least privilege, data encryption in transit and at rest; tenant isolation.
- Data Management: schema evolution support; late/duplicate event handling; GDPR-friendly deletion for personal data if any.

## 13. Configuration and Controls
- Risk parameters by scope (account/portfolio/global), effective dates, and approval workflows.
- Compliance rule sets per region/desk with versioning.
- Pricing policies (mark source hierarchy: last > mid > close) and FX conversion policies.

## 14. Reporting and Dashboards
- Real-time: order blotter, execution feed, positions, exposures, P&L, alerts.
- End-of-day: fills, allocations, positions, P&L summaries, exceptions.
- Drill-down: from portfolio → account → instrument → order → execution.

## 15. Testing and Acceptance
- Unit/integration tests for processors; replay tests for market data; order lifecycle scenarios (new, amend, partial fill, cancel).
- Risk/compliance rule tests with synthetic breaches.
- Acceptance criteria: end-to-end demo with live tick simulation, order through to fill, position/P&L update, risk breach alert, and audit trail visibility.

## 16. Open Questions
- Exact list of order types and venue-specific constraints.
- Preferred valuation policy per asset class; FX sources and refresh cadence.
- Compliance rule catalog and regional variations.
- Target limits and escalation matrix by desk/role.

## 17. Phased Delivery (suggested)
- Phase 1: Market data ingestion, basic OMS lifecycle, positions, real-time P&L (mid-mark), core risk limits, basic compliance checks, dashboards.
- Phase 2: Advanced routing/child orders, allocations, expanded surveillance, derivatives greeks, corporate actions.
- Phase 3: Stress scenarios, expanded reporting, rule catalogs, optimization hooks.
