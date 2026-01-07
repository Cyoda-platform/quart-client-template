# Trading Platform - Minimal MVP Requirements

## Overview
Build a minimal institutional trading platform supporting equities and basic derivatives (options and futures) with core capabilities for initial development and testing.

## Goals
- Deliver a working pipeline for real-time market data feeds, order entry, order lifecycle management, portfolio tracking, P&L calculations, risk checks, and basic compliance logging.
- Keep scope minimal: prioritize core paths for market data → order placement → execution confirmation → P&L update.

## Scope (MVP)
1. Market Data
   - Connect to a simulated real-time market data feed for equities and derivatives (no broker connectivity for MVP).
   - Provide subscription API for instruments and simple aggregation (bid/ask, last trade, volume).

2. Order Management System (OMS)
   - Support limit and market orders for equities; market and limit for derivatives.
   - Order lifecycle: New → Ack → Filled/PartialFill → Cancelled → Rejected.
   - Simple order matching simulator for execution.

3. Portfolio & Positions
   - Maintain positions by instrument with average price, quantity, realized/unrealized P&L.
   - Support basic position netting and per-account positions.

4. Risk Controls
   - Per-order checks: max order size, instrument-level limits, notional limits per account.
   - Blocking on violations with clear rejection codes.

5. Compliance & Audit
   - Immutable event log for orders, executions, and state transitions with timestamps and user IDs.
   - Basic trade reporting export (CSV) covering daily trades.

6. Real-time P&L
   - Mark-to-market using latest market data for unrealized P&L.
   - Real-time updates to portfolio P&L on each execution and market tick.

7. API & UX
   - REST API for order submission, cancellation, position queries, and market subscriptions.
   - Simple web UI to monitor orders, positions, and market data (basic dashboards).

8. Testing
   - Unit tests for OMS, matching engine, P&L calculations, and risk checks.
   - Integration tests using simulated market feed.

## Non-Goals (MVP)
- No production broker connectivity or clearing.
- No advanced strategy execution algorithms, smart order routing, or FIX connectivity.
- No multi-currency handling in initial MVP.

## Deliverables
- Working service with REST API and web UI running locally.
- Automated tests and CI setup for the branch.
- Documentation: setup guide and API reference.

## Next Steps
- Design entities (orders, trades, positions, instruments, accounts) and workflows (order lifecycle, market feed ingestion, P&L update).