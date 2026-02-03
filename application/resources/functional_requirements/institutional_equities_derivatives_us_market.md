# Institutional Equities & Derivatives — US Market (FIX, OMS, Risk/Clearing, Real-time P&L)

## Overview
Build an institutional trading platform that supports US equities and derivatives (options and futures). The system will provide:

- Real-time market data ingestion and normalization (multi-venue, NBBO consolidation)
- Advanced Order Management System (order lifecycle, algorithmic execution support, FIX connectivity)
- Portfolio tracking and position management with real-time P&L and margining
- Risk controls (pre-trade, intra-day, and post-trade) and clearing integration
- Regulatory compliance features: audit trails, trade surveillance, and reporting (including Reg NMS / Reg SHO considerations)
- Operational monitoring, alerting, and observability

## Scope
- Market data: consolidate feeds (SIP, proprietary venue feeds), normalize, and publish to internal event bus
- Execution: FIX connectivity to venues and brokers, support IOC/ FOK / GTC / Limit / Market orders, order splitting and child orders
- OMS: order lifecycle, execution reports, order amendments, cancellations, algo execution strategies (TWAP, VWAP, POV)
- Portfolio: per-account positions, multi-currency support, real-time P&L, mark-to-market and mark-to-model calculations
- Risk: credit limits, position limits, price-based checks, kill-switches, margin checks; integration with clearinghouses for margin and settlement
- Compliance: store immutable audit logs, generate regulatory reports, surveillance rules for wash trades, layering, spoofing detection
- Non-functional: low-latency for critical paths, scalability for high message throughput, high availability, secure authentication/authorization, encryption at rest/in-transit

## Integrations
- Market data adapters: SIP, Nasdaq, NYSE, CBOE; normalize to internal schema
- Execution: FIX adapters for broker/venue connectivity
- Clearing: connectivity to clearing members or clearinghouses (per client requirements)
- Reference data: securities master, corporate actions
- Time-series DB for market data and P&L history

## Data Models (high-level)
- Order: id, account_id, instrument_id, type, side, quantity, price, status, timestamps
- ExecutionReport: id, order_id, fill_qty, fill_price, venue, exec_time
- Position: account_id, instrument_id, quantity, avg_price, side, realized_pnl, unrealized_pnl
- MarketDataTick: instrument_id, bid, ask, last, timestamp, venue

## Operational Notes
- Observability: metrics for throughput, latency, error rates; tracing for order flows
- Deploy: containerized microservices, CI/CD driven by repo (GitOps), staging and production environments

## Acceptance Criteria
- System ingests and normalizes market data from at least two venues
- Orders can be submitted via FIX and processed through OMS with execution reports
- Real-time P&L calculated and available per account
- Risk limits enforced pre-trade and intra-day with configurable rules

## Assumptions
- Integration endpoints (FIX sessions, market data feeds) will be provided during integration phase
- Clearing/custody connections will be simulated until production credentials are available
