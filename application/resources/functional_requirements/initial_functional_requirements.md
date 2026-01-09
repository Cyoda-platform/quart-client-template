# Initial Functional Requirements

Project: Institutional Trading Platform (Python)
Focus: EU Markets (MiFID II)
MVP Priority: Low-latency market data & execution

Objectives:
- Provide real-time market data ingestion for equities and derivatives (level 1 and level 2 where available) from regulated EU venues.
- Implement a low-latency order execution path capable of handling market and limit orders with time-in-force options.
- Provide order lifecycle management (new, replace, cancel, fill) with state transitions persisted.
- Ensure regulatory compliance hooks for MiFID II (best execution recording, trade reporting, audit trails).
- Offer basic portfolio and position tracking with real-time P&L calculation for executed trades.
- Include pluggable risk checks (pre-trade and post-trade) to limit exposure per account and instrument.
- Provide logging and observability telemetry for latencies and throughput.
- Support integration points for market data providers, execution venues, and clearing/reporting.

MVP Non-functional Requirements:
- Target sub-100ms processing for market data ingestion and order placement within the core path.
- Horizontal scalability for market data workers and execution gateways.
- Secure credentials and secrets storage (delegated to environment infra).
- Modular design to support future addition of Smart Order Routing (SOR) and algorithmic execution strategies.

Deliverables:
- Functional requirements document (this file) saved in repository.
- Suggested Entities and Workflows for the Design phase.

