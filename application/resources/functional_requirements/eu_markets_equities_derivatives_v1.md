# Functional & Non-Functional Requirements: EU Markets (MiFID II, OTC derivatives) - V1

## Overview
A low-latency institutional trading platform supporting EU equities and OTC derivatives with MiFID II compliance and OTC reporting. V1 focuses on both equities and OTC derivatives with a strong emphasis on low latency (sub-10ms market data ingestion and order handling) while meeting regulatory needs.

## Functional Requirements

1. Market Data
   - Real-time market data feeds (Level 1 & 2) aggregator from multiple EU venues (e.g., LSE, Euronext, XETRA).
   - Timestamp normalization and feed handler with nanosecond precision.
   - Market data subscription management with dynamic subscription for symbols and instruments.

2. Order Management System (OMS)
   - Order lifecycle: new, partially filled, filled, canceled, rejected.
   - Order types: market, limit, iceberg, stop-limit, FOK, IOC.
   - Smart order routing across multiple execution venues with latency-aware routing decisions.
   - Pre-trade risk checks (max order size, exposure limits) and circuit breakers.

3. Trade Capture & Post-Trade
   - Real-time trade capture and confirmation.
   - Trade enrichment with venue, execution algo, latency metrics, and counterparty.
   - Support for OTC trade reporting formats (e.g., EMIR/ESAAT-compatible output).

4. Portfolio & Position Management
   - Real-time positions per instrument, account, and legal entity.
   - Holdings, average price, realized/unrealized P&L calculation in real-time.

5. Risk Controls
   - Real-time risk evaluation with incremental updates (VaR as plug-in), position limits, and margin checks.
   - Alerts and automated order throttling / kill-switch.

6. Compliance & Reporting
   - Detailed audit trail for order decisions and trade events (immutable, append-only logs).
   - MiFID II transaction reporting and OTC derivatives reporting (EMIR/ESAAT) with configurable reporting windows.

7. Monitoring & Observability
   - Latency dashboards, feed health indicators, and order processing metrics.
   - Distributed tracing for order lifecycle and market data path.

8. Integrations
   - Market data adapters for major EU venues and common market data protocols (FIX, proprietary binary feeds).
   - Connectivity to clearing providers for OTC derivatives.

## Non-Functional Requirements (prioritized: Low-latency)

- End-to-end latency target: sub-10ms for market data ingestion to OMS routing for core equites flows under typical load.
- Nanosecond-resolution timestamps on market data and execution events.
- Horizontal scalability with partitioning by instrument symbol and account where possible.
- High availability with failover strategies for feed handlers and order execution engines.
- Data retention: configurable retention periods for audit logs and reporting (hot storage for 90 days, cold for 7 years compliant with MiFID II).

## Constraints & Assumptions
- Initial deployment targets EU time zones and major venues.
- Connectivity to venue-specific gateways will be provided by the deployment environment.
- Clearing connectivity for derivatives will be bootstrapped in a later phase if external provider access is required.

## Deliverables for V1
- Functional requirements spec (this document saved in repository).
- Initial entity model (Orders, Trades, Positions, Instruments, Counterparties).
- Initial workflows: Order lifecycle, Trade capture & enrichment, P&L calculation, Reporting pipeline.
- CI pipeline for running unit and performance tests.
- Monitoring dashboards and observability hooks.

## Open Questions (for next iteration)
- Preferred market data vendors (direct or consolidated feeds)?
- Expected peak order rates / concurrency targets for sizing.
- Which clearing counterparties and reporting endpoints will be used for OTC derivatives?

-- End of Requirements --