# Real-Time Trading Platform - Functional Requirements

Overview
--------
A real-time trading platform supporting equities and derivatives with market data feeds, order management, portfolio tracking, risk controls, and regulatory compliance. The platform will be event-driven, low-latency, highly available, and auditable.

Core Entities
-------------
- Instrument
  - id: ISIN/FIGI/SYMBOL
  - type: EQUITY/OPTION/FUTURE
  - exchange
  - lot_size
  - currency

- MarketDataTick
  - instrument_id
  - timestamp
  - bid_price
  - bid_size
  - ask_price
  - ask_size
  - last_trade_price
  - last_trade_size
  - exchange

- Order
  - id
  - client_order_id
  - instrument_id
  - side: BUY/SELL
  - order_type: MARKET/LIMIT/STOP/ICEBERG
  - price
  - quantity
  - timestamp
  - status: NEW/PARTIAL_FILL/FILLED/CANCELLED/REJECTED
  - filled_quantity
  - remaining_quantity
  - time_in_force: GTC/IOC/FOK
  - account_id
  - routing_instructions

- Execution/Trade
  - id
  - order_id
  - execution_price
  - execution_quantity
  - counterparty
  - timestamp
  - venue

- Portfolio
  - id
  - account_id
  - positions: list of Position
  - cash_balance
  - realised_pl
  - unrealised_pl

- Position
  - instrument_id
  - quantity
  - average_price
  - side: LONG/SHORT

- Account
  - id
  - owner_name
  - margin_type
  - leverage
  - account_limits

- RiskProfile
  - account_id
  - max_position_size
  - max_exposure
  - max_order_value
  - allowed_instruments

- ComplianceEvent
  - id
  - type
  - details
  - timestamp
  - status

Workflows
---------
- Market Data Ingestion
  - Subscribe to market data feeds (FIX/Proprietary)
  - Normalize ticks into MarketDataTick entities
  - Publish ticks to internal event bus
  - Update L1/L2 aggregated state

- Order Lifecycle
  - Validate pre-trade (risk checks, compliance checks)
  - Accept/Reject new orders
  - Route orders to execution venues
  - Receive execution reports and update order status
  - Persist trades and update portfolio positions
  - Emit audit events for all state changes

- Portfolio & P&L Update
  - Recalculate positions on executions
  - Mark-to-market using latest market data
  - Recompute realised and unrealised P&L

- Risk Monitoring
  - Real-time checks (position limits, exposure, VaR thresholds)
  - Emit alerts and block orders if thresholds breached
  - Periodic batch risk reports

- Regulatory Reporting
  - Generate trade reports (FIX/CSV) for regulators
  - Maintain immutable audit logs for all orders and trades
  - Support trade reconstruction requests

Non-Functional Requirements
---------------------------
- Latency: market data processing < 10ms; order validation < 50ms
- Throughput: handle 50k ticks/sec, 5k orders/sec (scale horizontally)
- Durability: event sourcing for order/trade/audit events
- Availability: 99.99% SLA with multi-region deployment
- Observability: metrics, tracing, and centralized logging
- Security: role-based access control, encryption at rest and in transit

Risk & Compliance Controls
--------------------------
- Pre-trade checks: account limits, OFAC/sanctions screening, instrument eligibility
- Continuous surveillance: market abuse patterns, wash trades detection
- Audit trail: immutable event store with cryptographic hashes
- Data retention: configurable retention policies per regulatory jurisdiction

Deployment & Environment Notes
------------------------------
- Use event-driven architecture with message broker and processing workers
- Separate environments for dev/staging/prod
- CI/CD pipelines for builds and deployments
- Backup & disaster recovery plans

Next Steps
----------
1. Review and refine these requirements in Canvas (entities, workflows, and compliance rules).
2. Generate the application code from the finalized requirements (I can run generate_application when you’re ready).
3. Deploy a Cyoda environment in parallel so the app can be deployed and tested.

