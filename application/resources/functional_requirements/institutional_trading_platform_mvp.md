# Institutional Trading Platform — MVP Functional Requirements

Overview
--------
This document describes the Minimum Viable Product (MVP) requirements for an institutional trading platform supporting equities and derivatives across multiple jurisdictions (EU MiFID II / MiFIR, UK FCA, APAC exchanges such as SGX, HKEX, TSE). The platform focuses on connectivity, order management, market data, and client-facing APIs.

Must-have Functional Modules
----------------------------
- Real-time market data feeds (equities & derivatives) with market depth
- FIX connectivity and gateway (order entry / execution reports)
- Advanced Order Management System (smart order routing, algos, iceberg, TWAP/VWAP)
- Client APIs — FIX/REST for clients and downstream systems (settlement, clearing)

Functional Requirements
-----------------------
1. Market Data
   - Ingestion: Support multiple market data providers and exchange feeds via standard protocols (native, FIX/FAST, or WebSocket where provided).
   - Normalization: Normalize feed formats into a canonical MarketQuote model with fields for bid/ask levels, sizes, timestamps, instrument identifiers (ISIN, MIC), and implied volatility for derivatives.
   - Depth & Snapshot: Provide full order book depth (configurable levels) and snapshot + incremental updates with millisecond timestamps.
   - Replay & Recovery: Persist market data stream segments to enable replay, book reconstruction after outages, and gap detection.

2. FIX Connectivity
   - Session Management: Managed FIX sessions with per-counterparty configuration (heartbeat, resend strategy, sequence numbers). Support FIX 4.2+/5.0 where applicable.
   - Message Flows: Order entry, cancel/replace, execution reports, other execution lifecycle messages; support recovery and sequence resets.
   - Validation: Syntactic and semantic message validation with clear reject codes and audit trail entries.

3. Advanced Order Management System (OMS)
   - Order Types: Market, Limit, Stop, Stop-Limit, Iceberg, Pegged, Peg-to-Mid, TWAP, VWAP.
   - Smart Order Routing (SOR): Ability to route orders across multiple venues based on configurable routing policies (best-price, liquidity, fee-aware). Include venue adapters for major exchanges and broker gateways.
   - Algorithmic Execution: Support for TWAP/VWAP execution engines with configurable slice sizes, participation rates, and schedule windows.
   - Order State Machine: Deterministic state machine for order lifecycle with states for New, Acknowledged, PartiallyFilled, Filled, Rejected, Cancelled, Expired.
   - Risk Gates: Pre-trade checks integrated (max order size, credit limits per account, symbol trading permissions).

4. Client APIs & Integration
   - FIX API for institutional clients: session setup, order entry, market data subscriptions (where applicable), and execution reports.
   - REST API: For administration, order query, positions, market data snapshots, and settlement transfers.
   - WebSocket: For low-latency market data and order updates for web clients.
   - Authentication & Authorization: API keys, mTLS for FIX sessions, OAuth2 for REST, RBAC enforcement per-session.

Non-functional Requirements
---------------------------
- Latency: Sub-50ms for order acceptance paths; sub-5ms for internal messaging when possible (where exchange latency permits).
- Scalability: Horizontally scalable components for market data ingestion, order processing engines, and APIs.
- Reliability: High availability with automated failover for critical components (session managers, order engine).
- Observability: Extensive logging, metrics (per-venue latencies, order throughput), distributed tracing for order lifecycle.
- Security: Encrypted transport, secrets management, hardened host configuration, and role-based access control.

Compliance & Reporting
----------------------
- Trade Reporting: Capture and export trade reports in formats required by MiFID II / MiFIR, UK FCA, and APAC exchanges.
- Audit Trail: Immutable audit logs for order lifecycle, user actions, and system events with retention policy.
- Surveillance Hooks: Export trade and order activity to downstream surveillance tools or provide internal rule-based alerts.

Deliverables
------------
- Functional requirements doc (this file)
- High-level architecture diagram and component responsibilities
- API spec (OpenAPI and FIX session profiles)
- Initial set of entities and workflows in the repository for core models (Order, Trade, MarketQuote, Position)

Next Steps
----------
1. Review and confirm scope. 2. Generate Entities and Workflows for the core models. 3. Generate the initial application skeleton (generators) and wire up feed adapters.
