# Functional Requirements — Institutional Trading Platform

Overview
--------
An institutional trading platform with:

- Real-time market data feeds (equities & derivatives)
- Advanced order management system (OMS) with smart order routing
- Comprehensive portfolio tracking and real-time P&L
- Risk controls (pre-trade limits, real-time risk monitoring)
- Regulatory compliance features (audit trails, reporting, trade surveillance)
- Integration points for market data vendors and execution venues

Primary User Stories
--------------------
1. As a trader, I want to submit multi-leg orders and receive immediate execution feedback.
2. As a portfolio manager, I want real-time aggregated P&L and exposures per strategy.
3. As a risk officer, I want configurable pre-trade and post-trade risk checks.
4. As a compliance officer, I want immutable audit trails and exportable regulatory reports.

Non-functional Requirements
---------------------------
- Throughput: support 10k orders/sec across microservices
- Latency: sub-100ms order round-trip in normal conditions
- Availability: 99.99% with graceful degradation
- Data retention: immutable logs for 7 years for audit

Initial Integration Interfaces
------------------------------
- Market data (FIX/MD, websocket feeds)
- Execution venues (FIX/TCP, REST gateways)
- Reference data (prices, corporate actions)

Minimum Viable Scope (MVP)
--------------------------
- Real-time market data ingestion (websocket demo feed)
- Basic OMS (new/cancel/replace for single-leg orders)
- Portfolio service with real-time mark-to-market
- Simple risk engine with configurable per-account limits
- Audit trail logging for all orders and state changes

Next Steps
----------
- Generate entities for Order, Trade, Portfolio, Position, MarketSnapshot, RiskRule
- Design workflows: OrderLifecycle, TradeSettlement, EndOfDayPnl

