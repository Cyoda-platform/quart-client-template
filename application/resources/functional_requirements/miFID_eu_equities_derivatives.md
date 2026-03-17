# Functional Requirements — Institutional Trading Platform (EU / MiFID II)

## Overview
A platform for institutional trading covering EU equities and derivatives. Targets both buy-side (investment managers) and sell-side (brokers/market makers). Focus areas: low-latency order routing, comprehensive portfolio tracking, real-time P&L, risk controls, and MiFID II-compliant reporting and audit trails.

## Actors
- Buy-side: portfolio managers, traders, compliance officers
- Sell-side: brokers, market makers, execution traders
- System: market data feeds, order management system, risk engine, reporting service

## High-Level Requirements
1. Real-time market data ingestion
   - Support FIX and native exchange feeds
   - Market data normalization and time synchronization
2. Advanced Order Management System (OMS)
   - Multiple order types (limit, market, IOC, FOK, stop, TWAP)
   - Algo execution support (TWAP, VWAP, custom algos)
   - Order state machine with audit trail
3. Router & Execution
   - Smart order routing to lit and dark venues
   - Low-latency gateways for brokers/market makers
4. Portfolio & Position Management
   - Real-time P&L per strategy, account, and instrument
   - Position lifecycle management across cash and derivatives
5. Risk Controls
   - Pre-trade risk checks (size, limit, concentration)
   - Real-time mark-to-market and exposure limits
6. Regulatory & Compliance
   - MiFID II transaction reporting (TR) and order record-keeping
   - Ability to produce audit trails and surveillance reports
7. Reporting & Analytics
   - End-of-day and real-time reporting
   - Trade blotter, execution quality reports, performance attribution
8. Integration & APIs
   - REST and WebSocket APIs for order entry, market data, and reporting
   - Pub/Sub for internal components (event-driven)
9. Non-functional
   - High availability and horizontal scaling
   - Sub-second latencies for execution path
   - Secure multi-role access and audit logging

## Minimal Viable Set (MVP)
- Real-time level 1 market data ingestion and normalization
- Central OMS supporting basic order types and audit trail
- Simple order router with one simulated venue gateway
- Portfolio positions and P&L calculation per account
- Basic pre-trade risk checks and alerts
- MiFID II-compliant trade reporting module (skeleton)

## Open Questions
- Preferred market data providers and connectivity (FIX/ITCH)
- Matching engine requirements (in-house vs external)

## Acceptance Criteria (examples)
- System ingests market data with <200ms latency for L1 updates in normal load
- Orders progress through states with full audit trail persisted

## Next Steps
- Generate Entities (Order, Trade, Portfolio, Counterparty, Instrument)
- Design Workflows (Order lifecycle, Trade settlement, Reporting)
- Generate Application skeleton (MVP) in Python

