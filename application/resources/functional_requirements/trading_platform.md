# Trading Platform — Starter Functional Requirements

## Overview
Build a real-time trading platform supporting equities and derivatives (options/futures) with the following capabilities:

- Real-time market data ingestion (multiple feeds, price/size updates, level 1/2) with normalization and deduplication.
- Order Management System (OMS) supporting limit/market orders, order amendments, cancels, partial fills, and order lifecycle states.
- Execution Management with connectivity adapters to simulated/external brokers (FIX, REST) and smart order routing.
- Portfolio management tracking positions, cash, P&L, mark-to-market valuations, and trade history.
- Risk controls at order entry and portfolio level (pre-trade checks, position limits, margin checks, stress scenarios).
- Trade processing and settlement events with audit logs for regulatory compliance.
- Compliance monitoring and reporting (trade surveillance, trade reporting, audit trails).
- Instrument model for equities, options, and futures (symbols, expiries, strikes, option types).
- High-throughput, low-latency processing with robust error handling and retry semantics.

## Non-Functional Requirements
- Scalability: horizontal scale for market data ingestion and order processing.
- Latency: sub-second order handling for typical flows.
- Durability: persistent storage for trades, orders, positions, and audit logs.
- Observability: metrics, logs, and tracing for core services.
- Security: authentication, authorization, and encryption at rest/in transit.

## Core Modules & Responsibilities
1. Market Data Service
   - Ingest real-time feeds, normalize messages, publish to internal event bus.
   - Maintain best bid/ask and order book snapshots for instruments.

2. Order Management System (OMS)
   - Accept client orders, validate, route to execution adapters, handle state transitions, and persist order events.

3. Execution Adapters
   - Connect to external brokers (or simulated ones) via FIX and REST APIs.
   - Support recoverable connections and idempotent delivery.

4. Portfolio Service
   - Maintain positions, cash balances, P&L, and support mark-to-market.

5. Risk Engine
   - Pre-trade checks (max order size, position limit, margin check), portfolio-level risk scoring, and configurable rules.

6. Trade Processor & Settlement
   - Ingest fills, update positions and cash, generate settlement instructions, and write audit events.

7. Compliance & Reporting
   - Record audit trails, suspicious trade detection rules, and generate regulatory reports.

## Data Models (high level)
- Instrument: symbol, asset_type (equity/option/future), exchange, expiry, strike, option_type
- MarketData: instrument_id, bid, ask, bid_size, ask_size, timestamp, source
- Order: order_id, client_id, instrument_id, side, order_type, quantity, price, status, created_at
- Trade: trade_id, order_id, instrument_id, quantity, price, side, timestamp, execution_venue
- Position: account_id, instrument_id, quantity, avg_price, realized_pnl, unrealized_pnl
- RiskProfile: account_id, limits, margin_requirements, risk_score
- ComplianceEvent: event_id, type, details, timestamp

## Workflows (high level)
- MarketData Ingestion → Normalize → Publish
- Order Entry → Pre-trade Risk Checks → Route to Execution → Confirm/Filled → Trade Processing
- Trade Processing → Update Positions → Revalue Portfolio → Trigger Risk Alerts/Reports

## Next Steps
- Create concrete entity JSON files for key models (Instrument, MarketData, Order, Trade, Position, RiskProfile, ComplianceEvent).
- Define workflows in JSON and validate them.
- Generate processors for market data ingestion, order processing, risk checks, and trade processing.
- Start a full build once design artifacts are finalized.

---

Please review this starter requirements doc. If you'd like changes, tell me what to modify, or say "Approve" to proceed to entity generation.