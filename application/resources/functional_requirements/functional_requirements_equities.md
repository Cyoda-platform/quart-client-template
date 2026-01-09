# Functional Requirements — Institutional Trading Platform (Equities Only)

## Overview
This document describes the initial functional requirements for an institutional trading platform focused on equities. The system will provide:

- Real-time market data ingestion and distribution
- Advanced order management system (OMS) with order lifecycle management
- Portfolio tracking and real-time P&L calculations
- Risk monitoring and pre-trade/post-trade risk checks
- Regulatory compliance features (audit trails, trade reporting, FIX connectivity)
- Connectivity to market data vendors and broker/exchange endpoints

## Scopes and Priorities
1. Real-time market data (high priority)
2. OMS core functionality (high priority)
3. Portfolio & P&L (high priority)
4. Risk controls (medium priority)
5. Compliance and reporting (medium priority)
6. Admin & Ops (low priority)

## Key Functional Requirements

1. Market Data
   - Connect to real-time market data feeds (level 1 and aggregated order book snapshots)
   - Normalize feeds into internal market data events
   - Provide subscription model for downstream consumers (OMS, risk, UI)

2. Order Management
   - Support order types: MARKET, LIMIT, STOP, IOC, FOK
   - Order lifecycle: NEW → PENDING → ACKNOWLEDGED → PARTIAL_FILL → FILLED → CANCELED → REJECTED
   - Support multi-leg orders and order tags/algorithms
   - FIX protocol support for broker connectivity

3. Portfolio & P&L
   - Real-time position tracking per account and global
   - Real-time mark-to-market P&L using latest market data
   - Trade booking, allocations, and corporate actions adjustments

4. Risk Controls
   - Pre-trade checks: credit limit, max order size, position limits
   - Post-trade checks: exposure tracking, limit breaches alerts
   - Circuit breakers and kill-switches for emergency scenarios

5. Compliance & Reporting
   - Immutable audit trail for all order and trade events
   - Trade reporting in required formats (e.g., TRACE, local regulator APIs)
   - User access controls and activity logging

6. Non-functional
   - Low latency for OMS and market data paths
   - High availability and graceful degradation
   - Observability: metrics, traces, structured logs

## Deliverables
- Functional requirements markdown (this doc) — committed to repo
- Suggested next artifacts: Entities (Order, Trade, Position, MarketData, Account), Workflows (OrderLifecycle, TradeSettlement, PnLUpdate), Acceptance Criteria


## Future Extensions
- Add derivatives and multi-asset support
- Advanced analytics (algo strategies, transaction cost analysis)

