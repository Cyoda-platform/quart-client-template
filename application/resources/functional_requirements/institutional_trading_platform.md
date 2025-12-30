# Institutional Trading Platform — Functional Requirements

Overview
--------

This document defines the functional requirements for an institutional trading platform that supports:

- Real-time market data feeds (equities & derivatives)
- Advanced order management system (OMS)
- Comprehensive portfolio tracking and real-time P&L
- Risk controls (pre-trade and post-trade)
- Regulatory compliance (audit trails, reporting)
- Integration adapters (exchanges, custodians, market data providers)

Design Principles
-----------------

- Event-driven architecture using Cyoda processors and workflows
- Clear separation of concerns: market data ingestion, order lifecycle, portfolio state, risk checks, reporting
- Highly observable: metrics, audit logs, and traceability for every message
- Scalable and resilient: stateless processors where possible, durable state for positions/ledgers

Requirements
------------

1. Market Data
   - Ingest real-time market data for equities and derivatives from multiple providers.
   - Normalize instrument identifiers (ISIN, CUSIP, ticker) and map to internal instrument definitions.
   - Provide time-series storage for tick-level and aggregated data (1s/1m bars).
   - Support snapshot, incremental, and recovery feeds.

2. Order Management System (OMS)
   - Support order types: MARKET, LIMIT, STOP, STOP_LIMIT, FOK, IOC, and iceberg orders.
   - Maintain full order lifecycle: NEW -> ACKED -> PARTIALLY_FILLED -> FILLED -> REJECTED -> CANCELED.
   - Support child/parent orders for algo execution and conditional orders (e.g., peg to mid).
   - FIX gateway adapter for connectivity to brokers/exchanges.
   - Order routing rules, smart order routing, and execution cost modeling.

3. Portfolio & Positions
   - Maintain real-time positions per account and per strategy.
   - Ledger-based cash accounting with support for multiple currencies.
   - Instrument valuation (mark-to-market) with support for FX conversion and derivative pricing models.
   - Real-time P&L calculations (unrealized, realized, fees, commissions).

4. Risk Controls
   - Pre-trade checks: credit limits, position limits, price checks, order size checks.
   - Post-trade checks and reconciliation against execution reports.
   - Margin calculations for derivatives and collateral management.
   - Alerts and automated kill-switches for breaches.

5. Compliance & Reporting
   - Immutable audit trails for orders, executions, and state changes with timestamps and actor metadata.
   - Regulatory reporting interfaces for trade reporting (e.g., EMIR, MiFIR) — extensible connectors.
   - Data retention policies and secure access controls.

6. Instruments
   - Support for equities (cash), options, futures, swaps, and other derivatives.
   - Instrument definitions with lifecycle events (exercise, expiry, corporate actions).

7. Integrations
   - Adapters for market data providers, FIX gateways, broker APIs, clearing/custodian APIs.
   - Monitoring and health checks for adapters with automatic failover.

8. Operational & Non-Functional
   - SLAs for data freshness and order ACK latencies.
   - Observability: metrics, traces, logs, and dashboards in Cyoda Cloud.
   - Security: authentication, authorization, encryption in transit and at rest.

Canvas Guidance
---------------

- Entities: Instrument, MarketTick, Order, Trade, Position, Account, Strategy, RiskProfile, LedgerEntry
- Workflows: OrderLifecycle, TradeSettlement, PositionUpdate, RiskCheck
- Processors: MarketDataNormalizer, FIXAdapter, OrderRouter, PnLCalculator, MarginCalculator

Next steps
----------

1. Review this requirements document in Canvas and edit as needed.
2. Add or attach any API specs, FIX protocol docs, or derivative pricing models.
3. When you're happy with the design, we can generate the application code (full build) or incrementally add entities/workflows with the CLI.

Would you like me to commit this to the branch now and open the Canvas editor for you?