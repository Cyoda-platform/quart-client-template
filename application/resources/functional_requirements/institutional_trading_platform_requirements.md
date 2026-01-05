# Institutional Trading Platform — Functional Requirements

Version: 1.0
Branch: 4aecb9cf-e79c-4980-8f77-ea79de7fa057
Date: 2026-01-05
Author: github_agent (initial draft)

## Purpose
Provide a single-source functional requirements document for an institutional trading platform that supports equities and derivatives. The system will provide real-time market data ingestion, advanced order management, execution routing, portfolio/position management, risk monitoring, compliance checks, and real-time P&L calculation.

## Scope
In-scope:
- Market data ingestion (tick and level-2 snapshots)
- Order lifecycle management and execution (
  New, Ack, Partial Fill, Filled, Canceled, Rejected)
- Execution/Trade capture and reconciliation
- Portfolio and position aggregation across accounts
- Real-time P&L (trade+market-data driven)
- Pre-trade and continuous risk monitoring with blocking capability
- Compliance checks and surveillance triggers
- Connectivity placeholders for exchange/FIX adapters and venue routing
- Support for equities and listed/cleared derivatives

Out-of-scope (initial):
- Clearing house integrations beyond trade capture
- Back-office settlement workflows
- Historical tick storage and long-term analytics (may be added later)

## High-level Components
1. Market Data Feed
   - Supports top-of-book ticks and level-2 snapshots for multiple instruments
   - Ingest frequency: up to 50,000 updates/sec aggregate (target sizing)
   - Typical attributes: instrument_id (ISIN/SYMBOL), timestamp (ISO 8601 UTC), bid/ask levels, size, trade price/size

2. Order Management System (OMS)
   - Order entity with lifecycle states: NEW -> ACK -> PARTIAL_FILL -> FILLED -> CANCELED -> REJECTED
   - Support for limit, market, pegged orders and basic algo flags
   - OMS processors: validate, route, cancel, modify, handle fills and ACKs

3. Execution / Trade Entity
   - Captures fills from venues: trade_id, execution_venue, instrument_id, price, quantity, timestamp, counterpart (placeholder)
   - Reconciliation processor to link Trades to Orders

4. Portfolio & Positions
   - Portfolio entity aggregates positions by instrument across accounts
   - Position entity: instrument_id, quantity, average_price, realized_pnl, unrealized_pnl
   - Processors to apply trades to positions and recompute aggregates

5. Risk Controls
   - Risk Profile entity per desk/account with limits: max_notional, max_delta, max_exposure
   - Risk Monitoring workflow: pre-trade checks (block or alert), continuous scans (scheduled/streaming) with actions ALERT or BLOCK

6. Compliance
   - Compliance Event entity to capture surveillance signals
   - Compliance workflow: pre-trade checks for regulatory rules (e.g., short-sale flags, order to self-check), post-trade surveillance triggers

7. Real-time P&L
   - P&L workflow consumes market data and trade events to compute position-level and portfolio-level P&L
   - Calculate realized and unrealized P&L and a running intraday P&L

8. Connectivity
   - Connectivity placeholders for exchange adapters and FIX gateway configs
   - Adapter config includes host/port placeholders, credentials (secrets stored separately), and routing rules per instrument/venue

## Data Vendors & Execution Venues (Assumptions)
- Market data vendor: generic streaming feed (placeholder)
- Execution venues: multiple (lit exchanges, dark pools, broker APIs) — model as named venues with routing priority lists
- Regulatory regions: US and EU (assume Reg SHO, MiFID II considerations)

## Non-Functional Requirements
- Latency targets:
  - Pre-trade risk check decision: <= 10 ms (goal)
  - Order acceptance and routing latency: <= 50 ms (goal)
  - Market data ingestion latency: <= 5 ms end-to-end (goal)
- Throughput:
  - Support up to 50k market updates/sec and 5k orders/sec initially (scale horizontally)
- Availability: 99.9% per trading day SLA (target)
- Security:
  - Authentication and authorization placeholders (API keys, role-based access)
  - Secrets and credentials are stored in secure Cyoda-managed environment variables (placeholders in configs)

## Regulatory & Audit
- Keep audit trails for order lifecycle events, trade executions, compliance decisions, and risk blocks
- Capture timestamps in ISO 8601 UTC with monotonic sequence IDs for event ordering
- Provide exportable logs for regulatory inspection (US & EU requirements)

## Acceptance Criteria
- Market data ingested and materialized to market data entity with sample instruments
- Orders progress through defined lifecycle with processors triggering state transitions
- Trades are captured and applied to positions, and P&L updates reflect trade+market data
- Pre-trade risk checks can return ALERT or BLOCK and are enforced for blocked orders
- Compliance checks can flag events and create Compliance Event records

## Integration / Next Steps
- Wire up concrete adapters for chosen market data vendors and execution venues (config placeholders exist)
- Define per-instrument routing rules and priority tables
- Define detailed risk rule list and thresholds (example: max_notional per instrument)

## Notes / Placeholders
- Credentials, secrets, and third-party vendor endpoints are intentionally left as placeholders. Use Cyoda environment secrets to store these values.

---

End of requirements document.
