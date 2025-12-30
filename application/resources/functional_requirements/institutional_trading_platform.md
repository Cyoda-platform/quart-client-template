# Institutional Trading Platform – Functional Requirements

Version: 1.0
Status: Draft
Owner: Trading Technology
Last Updated: {{DATE}}

## 1. Objective
Design and implement an institutional-grade trading platform covering real-time market data, advanced order management, portfolio tracking, risk controls, regulatory compliance for equities and derivatives, and real-time P&L, built as an event-driven Cyoda application.

## 2. In Scope
- Asset classes: Equities (cash), Equity options, Index futures, Single stock futures
- Capabilities:
  - Real-time market data ingestion and normalization
  - Advanced Order Management System (OMS)
  - Trade capture and allocation
  - Portfolio, positions, exposures
  - Real-time P&L (intraday and EOD)
  - Risk controls (pre-trade, at-trade, post-trade) and alerts
  - Regulatory/compliance checks (pre-/post-trade), surveillance hooks, audit trail
  - Corporate actions adjustments (splits, dividends where relevant)
  - Reconciliation (orders vs executions, positions vs trades)

## 3. Out of Scope (Initial Release)
- Fixed income, FX, crypto
- Smart order routing optimization beyond venue selection rules
- Complex exotics, path-dependent derivatives
- Historical analytics beyond required backfills for EOD

## 4. Personas & Roles
- Trader: Enters/amends/cancels orders, monitors fills, P&L
- Portfolio Manager: Monitors exposures, portfolio P&L, rebalancing
- Risk Officer: Sets limits, monitors breaches, approves overrides
- Compliance Officer: Reviews breaches, restricted lists, approvals, audit
- Operations: Allocations, breaks, reconciliations, EOD processes
- System Admin: User/RBAC, configuration, static data

RBAC (examples):
- Trader: Create/Amend/Cancel Orders, View Market Data, View Own P&L
- PM: View All Portfolios, Rebalance (orders via desk)
- Risk: Configure Limits, Approve Overrides, View All Data
- Compliance: Manage Rules, Approvals, Audit Views
- Ops: Allocations, Break Management, EOD Rollups
- Admin: User, Venue, Instrument static management

## 5. Core Entities (Indicative)
- Instrument: {symbol, isin, assetClass, contractSpecs, tickSize, currency}
- Venue: {venueCode, name, sessionHours}
- MarketDataTick: {instrumentId, venueCode, ts, bid, ask, last, bidSize, askSize, lastSize}
- Quote: {instrumentId, mid, spread, ts}
- Order: {orderId, parentId?, accountId, instrumentId, side, qty, tif, orderType, price?, stopPrice?, status, route, traderId, ts}
- OrderLeg: {orderId, legId, instrumentId, qty, type}
- ExecutionReport: {execId, orderId, ts, price, qty, venue, liquidityFlag}
- Trade: {tradeId, orderId, instrumentId, qty, price, side, ts, accounts[], fees}
- Allocation: {tradeId, accountId, qty, method}
- Position: {accountId, instrumentId, netQty, avgPrice, openPnL, realizedPnL}
- Portfolio: {portfolioId, accounts[], exposures, greeks?}
- RiskLimit: {limitId, scope(account|desk|firm), metric(notional|qty|vega|delta), threshold, breachPolicy}
- ComplianceRule: {ruleId, name, type(pre|post), criteria, action(block|warn|approve)}
- PnL: {portfolioId|accountId|deskId, instrumentId?, realized, unrealized, total, ts}
- CorporateAction: {instrumentId, type(split|dividend), effectiveDate, factor}
- User: {userId, role, permissions}

## 6. Event Model (Key Events)
- MarketDataReceived
- QuoteUpdated
- OrderSubmitted
- OrderValidated
- OrderRouted
- OrderAcknowledged
- OrderRejected
- OrderAmended
- OrderCancelled
- ExecutionReceived
- TradeBooked
- AllocationCreated
- PositionUpdated
- PnLUpdated
- RiskCheckTriggered
- RiskBreachDetected
- ComplianceCheckTriggered
- ComplianceApproved
- ComplianceRejected
- CorporateActionApplied
- ReconciliationBreakDetected
- ReconciliationResolved
- EndOfDayRollupCompleted

## 7. Workflows (High-level)
1) Market Data Ingestion & Normalization
- Input: MarketDataReceived
- Process: Normalize ticks, compute mid/spread (QuoteUpdated), publish quotes
- Output: QuoteUpdated events, cache latest for pricing/P&L

2) Order Lifecycle (Pre-trade → Route → Execution → Amend/Cancel)
- Trigger: OrderSubmitted
- Steps:
  - Pre-trade validations: instrument tradability, session, quantity precision
  - Pre-trade compliance: restricted lists, short-sale marking, wash-trade checks
  - Risk checks: notional/qty/greeks vs RiskLimit, credit checks
  - If pass: OrderValidated → route (OrderRouted)
  - Await venue ack: OrderAcknowledged or OrderRejected
  - Amend/Cancel: OrderAmended/OrderCancelled with re-validation

3) Execution Processing & Trade Booking
- Trigger: ExecutionReceived
- Steps: Match to order, update order status, book TradeBooked, compute fees, liquidity flags, update allocations when requested

4) Positions & Portfolio
- Trigger: TradeBooked → PositionUpdated
- Aggregate by account/portfolio; incorporate corporate actions; produce exposures

5) Real-Time P&L
- Inputs: PositionUpdated, QuoteUpdated
- Compute unrealized: (marketPrice - avgPrice) * qty; realized on TradeBooked
- Publish PnLUpdated per account/portfolio/instrument

6) Risk Monitoring & Alerts
- Triggers: OrderSubmitted, PositionUpdated, PnLUpdated, QuoteUpdated
- Evaluate RiskLimit metrics; emit RiskBreachDetected; route to Risk for approval/override when configured

7) Compliance (Pre/Post)
- Pre-trade checks block/warn; post-trade surveillance hooks create alerts for review
- Events: ComplianceCheckTriggered, ComplianceApproved/Rejected

8) EOD Rollup & Reconciliation
- Aggregate final positions/P&L; compare orders vs executions and positions vs trades
- Emit EndOfDayRollupCompleted; detect and manage reconciliation breaks

## 8. OMS Requirements
- Order types: Market, Limit, Stop, Stop-Limit, Iceberg (displayQty), Pegged (mid/primary/market)
- TIF: Day, IOC, FOK, GTC
- Advanced: Parent/child, staged orders, bulk cancel by filter, kill-switch per desk
- Routing: Venue selection by instrument/venue status; failover route on venue reject
- Idempotency: orderId uniqueness; safe retries
- Rate limiting/throttling per venue
- Partial fills and average price handling
- Amend rules: price/qty changes with re-validation

## 9. Risk Controls
- Pre-trade: Max order size, notional cap, price collars, credit exposure, short-sale eligibility
- At-trade: Slippage checks, duplicate execution detection
- Post-trade: Concentration limits, net exposure, Greeks (delta/vega) for options/futures
- Limit policies: block, warn+escalate, allow with approval window
- Overrides: captured with approver, reason, timestamp

## 10. Compliance Requirements
- Pre-trade: Restricted lists, watch lists, short-sale flags, best-ex rules check hints
- Post-trade: Surveillance hooks (wash trades, layering/spoofing indicators), trade reporting interface
- Full audit trail of orders, changes, approvals, breaches, and user actions
- Retention and immutable logs per policy

## 11. Portfolio & Positions
- Multi-account, multi-portfolio hierarchies
- Real-time net/gross exposures by instrument, sector, currency
- Derivatives support: contract multiplier, theoretical price inputs
- Corporate actions engine: splits/adjustments affect positions and avg price

## 12. Real-Time P&L
- Price sources: last, bid/ask midpoint with fallback
- Realized on trades (fees included); unrealized on quotes/positions
- Dimensions: by account, portfolio, desk, instrument
- Snapshots with timestamps; intraday roll-forward; EOD freeze

## 13. APIs & Interfaces (indicative)
- REST (examples):
  - POST /orders
  - PATCH /orders/{orderId}
  - DELETE /orders/{orderId}
  - GET /orders?status=...
  - GET /positions?accountId=...
  - GET /pnl?portfolioId=...
  - GET /limits
  - POST /allocations
- Streaming:
  - WebSocket topics: quotes.{instrumentId}, orders.{accountId}, pnl.{portfolioId}
- Events (topics): marketdata.*, orders.*, executions.*, trades.*, positions.*, pnl.*, risk.*, compliance.*

## 14. Data Quality & Reconciliation
- Duplicate detection on market data and executions
- Sequence gaps, late/out-of-order handling
- Reconciliation jobs: orders vs executions; trades vs positions; alert on breaks

## 15. Non-Functional Requirements
- Latency targets:
  - Market data processing p50 < 20ms, p99 < 100ms
  - Order validation + route p50 < 50ms, p99 < 200ms
  - P&L update propagation p50 < 50ms, p99 < 200ms
- Throughput: sustain 5k ticks/sec and 200 orders/sec firmwide (configurable)
- Availability: 99.9% trading hours
- Resilience: retry policies, backpressure, circuit breakers
- Consistency: Idempotent processors; exactly-once effects for booking
- Security: RBAC, least privilege, encryption in transit/at rest, secrets management
- Auditability: immutable append-only log of key actions
- Observability: metrics, logs, traces; dashboards for workflows and SLAs; alerting

## 16. Controls & Governance
- Change management: versioned workflows and entities; canary toggles where applicable
- Segregation of duties: approvals required for overrides and rule changes
- Data retention: configurable by entity/event type; EOD archives
- Privacy: PII minimization; access logging

## 17. Acceptance Criteria (Samples)
- Pre-trade risk blocks orders breaching hard notional limits; audit shows reason
- Compliance restricted symbol list blocks corresponding orders; approval path works
- ExecutionReceived → TradeBooked within 100ms p95 under 200 execs/sec
- PnLUpdated published within 200ms of QuoteUpdated for active positions
- CorporateActionApplied adjusts positions/avgPrice correctly for 2:1 split
- ReconciliationBreakDetected raised when execution without matching order appears

## 18. Test Scenarios (Samples)
- Spike test: 10k ticks/sec for 60s; no data loss; p99 latency within target
- OMS: partial fill flow with amend down then cancel; correct average price
- Risk: override workflow with Risk approval captured in audit trail
- Compliance: post-trade surveillance alert for rapid order cancels sequence
- EOD: Rollup with multiple portfolios; correct totals; immutable snapshot

## 19. Configuration & Static Data
- Venue trading sessions, holidays
- Instrument tick size, lot size, contract multipliers
- Risk limit catalog and policies
- Compliance rule catalog and restricted lists

## 20. Open Questions
- Exact venue connectivity set for Phase 1
- Fees model details per venue and instrument
- Required compliance reporting formats and schedules
- Target throughput per desk and firm limits
- Corporate actions scope beyond splits/dividends

## 21. Assumptions
- Market data includes best bid/ask and last trade with sizes
- Derivatives Greeks supplied externally or computed from available parameters
- All times are UTC; trading sessions mapped per venue

## 22. Glossary
- OMS: Order Management System
- P&L: Profit and Loss
- TIF: Time in Force
- EOD: End of Day
- RBAC: Role-Based Access Control
