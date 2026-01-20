# Functional Requirements: Exchange + OTC + Prime Broker OMS

## Scope
Build an advanced Order Management System (OMS) focusing on Exchange-listed and OTC derivatives with Prime Broker integration. The initial phase emphasizes FIX gateway support for market connectivity.

## Objectives
- Provide low-latency order routing via FIX gateways to multiple exchanges and liquidity venues.
- Support OTC derivative trade capture and lifecycle management, including confirmations and novations with prime brokers.
- Integrate prime broker margin and collateral workflows.
- Real-time P&L calculation and exposure tracking across venues.
- Audit trails, trade reporting, and regulatory compliance hooks.

## Core Features (MVP)
1. Connectivity
   - FIX gateway implementation for inbound/outbound order flows (support FIX 4.2 - 5.0)
   - Market data adapters for exchange feeds and consolidated tape
   - Centralized connection manager for brokers and venues

2. Order Management
   - Order lifecycle: New, Modified, Canceled, Rejected, Filled, Partially Filled
   - Order types: Market, Limit, Stop, Iceberg, TWAP/VWAP strategies
   - Execution algorithms and route optimization

3. OTC Support
   - Trade capture for swaps, forwards, options (vanilla and selected exotics)
   - Confirmation workflows with counterparties and prime brokers
   - Netting and trade compression hooks

4. Prime Broker Integration
   - Margin queries and initial/variation margin workflows
   - Trade novation and custody instructions
   - Collateral management basics (cash and simple securities)

5. Risk & P&L
   - Real-time P&L per account, desk, and portfolio
   - Market risk metrics (delta, vega for options) for core instruments
   - Position limits and pre-trade checks

6. Compliance & Auditing
   - Trade reporting outputs (configurable per jurisdiction)
   - Immutable audit logs for order and trade events

## Non-Functional
- Target latency goals for FIX round-trips (configurable)
- High availability for critical services (FIX gateway, order router)
- Observability: metrics, tracing, and logging

## Integrations
- FIX gateways
- Market data feeds
- Prime broker APIs (REST/FIX)

## Acceptance Criteria (MVP)
- Successful end-to-end order routing via FIX to at least one exchange simulator
- Capture and lifecycle management of OTC trades with confirmations
- Real-time P&L calculations validated against trade blotter

## Next Steps
- Define Entities: Order, Trade, Counterparty, Position, Portfolio, RiskProfile
- Design Workflows: OrderRouting, TradeLifecycle, MarginCalculation

