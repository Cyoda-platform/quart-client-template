# MVP Requirements: Real-time Market Data + Low-Latency P&L

Overview
--------
Build an MVP for US equities focusing on real-time market data ingestion, tick processing, and low-latency real-time P&L calculations suitable for institutional use.

Core Functional Requirements
----------------------------
1. Market Data Ingestion
   - Connect to market data providers (e.g., SIP/CTA, proprietary feeds) via streaming APIs and a simulated feed adapter for testing.
   - Support top-of-book and full order book snapshots.
   - Ensure message ordering and timestamp handling for accurate time-series reconstruction.

2. Tick Processing & Normalization
   - Normalize incoming ticks into a canonical internal format (symbol, exchange, timestamp, bid, ask, bid_size, ask_size, last_price, last_size).
   - Deduplicate events and handle out-of-order arrivals with an event-time watermark strategy.
   - Support per-symbol aggregation (1ms, 10ms, 100ms buckets) and high-throughput processing.

3. Real-time P&L Engine
   - Maintain per-account and per-portfolio positions in-memory with optional periodic persistence.
   - Calculate unrealized and realized P&L in real-time using mark-to-market from incoming ticks.
   - Support concurrency-safe updates for high-frequency trade events and market updates.

4. Low-Latency Architecture
   - Use async, non-blocking I/O (asyncio) and in-memory structures optimized for low latency.
   - Provide a message buffering and backpressure mechanism to avoid data loss under burst traffic.

5. Monitoring & Observability
   - Instrument ingestion latency, processing latency, and P&L calculation latency.
   - Emit metrics and structured logs for debugging and SLA tracking.

6. Testing & Simulation
   - Include a market data simulator that can replay historical ticks at configurable speeds and inject synthetic out-of-order messages.
   - Unit and integration tests for tick normalization and P&L correctness.

Non-Functional Requirements
---------------------------
- Latency: Target sub-10ms end-to-end processing for top-of-book updates to P&L update in typical loads.
- Throughput: Support >50k ticks/s in aggregate with horizontal scaling assumptions.
- Consistency: Strong consistency for P&L calculations within a single node; eventual consistency acceptable across nodes for scale-out.
- Security & Compliance: Audit logs for all market data and P&L updates; secure communication channels.

Deliverables
------------
- Functional requirements document (this file)
- Market data ingestion adapter scaffold
- Tick normalization module
- In-memory position store and P&L engine
- Market simulator and test suites

Next Steps
----------
I will save this into the repo at application/resources/functional_requirements/real_time_market_data_low_latency_pnl_mvp.md.

Based on these requirements, we should define Entities like `MarketTick`, `Position`, `Portfolio`, and `PnLEntry`, and Workflows like `TickIngestion -> Normalize -> UpdatePositions -> RecalculatePnL`.

Would you like me to generate the entities, design the workflows, or generate the full application now?

