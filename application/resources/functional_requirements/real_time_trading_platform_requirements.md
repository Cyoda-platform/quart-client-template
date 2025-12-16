# Real-Time Trading Platform - Functional Requirements

## Overview
A real-time trading platform supporting equities and derivatives. Core capabilities:

- Market data ingestion and processing (ticks, level-2 order book snapshots)
- Order management system (OMS) supporting market, limit, stop, and algo orders
- Order routing and execution, including partial fills and cancellations
- Trade matching and confirmations
- Portfolio tracking and position management across accounts
- Real-time risk controls and pre-trade checks (limits, margin, credit)
- Regulatory compliance: audit trail, reporting, trade surveillance
- Persistence, reconciliation, settlement interfaces, and reporting APIs

## Non-Functional Requirements
- Latency targets (e.g., sub-5ms network latency for internal matching)
- High throughput (tens of thousands of messages/sec)
- High availability and fault tolerance
- Secure access controls and audit logging
- Data retention and privacy controls

## Functional Areas
1. Market Data
   - Connect to market data feeds
   - Normalize and enrich instrument data
   - Maintain order book and publish updates to interested services

2. Order Management
   - Create, amend, cancel orders
   - Support order states (New, PartiallyFilled, Filled, Cancelled, Rejected)
   - Execution reports and FIX/API adapters

3. Execution & Matching
   - Matching engine for order books
   - Support for derivatives-specific behaviors (expiry, exercise)

4. Portfolio & Positions
   - Real-time positions per account and consolidated
   - P&L calculations and valuation

5. Risk Controls
   - Pre-trade checks and hard/soft limits
   - Real-time margin calculations and alerts

6. Compliance & Audit
   - Immutable audit trail for order and trade events
   - Reporting connectors and surveillance hooks

## Next steps
- Generate Entities and Workflows from these requirements
- Start building the application (generate_application) once the requirements are finalized
