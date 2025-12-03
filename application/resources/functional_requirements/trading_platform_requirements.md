# Real-Time Trading Platform Requirements

## Overview
Build a comprehensive real-time trading platform supporting equities and derivatives with market data feeds, order management, portfolio tracking, risk controls, and regulatory compliance.

## Core Entities

### 1. Instrument
- **Purpose**: Represents tradeable securities (equities, derivatives, bonds, etc.)
- **Key Fields**: symbol, name, instrument_type, exchange, currency, contract_specs
- **Business Rules**: Unique symbol per exchange, valid instrument types
- **Workflow**: created -> validated -> active -> (suspended) -> delisted

### 2. MarketData
- **Purpose**: Real-time market data feeds and pricing information
- **Key Fields**: instrument_id, price, volume, bid, ask, timestamp, data_source
- **Business Rules**: Price validation, timestamp ordering, data quality checks
- **Workflow**: received -> validated -> processed -> published

### 3. Order
- **Purpose**: Trading orders with complete lifecycle management
- **Key Fields**: order_id, instrument_id, side, quantity, price, order_type, client_id
- **Business Rules**: Risk limits, market hours, position limits, compliance checks
- **Workflow**: submitted -> validated -> risk_checked -> compliance_approved -> executed -> settled

### 4. Position
- **Purpose**: Current holdings and positions per instrument and client
- **Key Fields**: client_id, instrument_id, quantity, average_price, market_value, unrealized_pnl
- **Business Rules**: Position reconciliation, mark-to-market updates
- **Workflow**: opened -> updated -> closed

### 5. Portfolio
- **Purpose**: Aggregated portfolio view and performance tracking
- **Key Fields**: client_id, total_value, cash_balance, positions, daily_pnl, risk_metrics
- **Business Rules**: Portfolio aggregation, performance calculation, risk attribution
- **Workflow**: created -> calculated -> updated -> reported

### 6. RiskControl
- **Purpose**: Risk limits and real-time monitoring
- **Key Fields**: client_id, limit_type, limit_value, current_exposure, breach_threshold
- **Business Rules**: Real-time limit monitoring, breach notifications, automatic controls
- **Workflow**: defined -> active -> monitored -> (breached) -> resolved

### 7. ComplianceRecord
- **Purpose**: Regulatory compliance tracking and reporting
- **Key Fields**: record_type, client_id, order_id, rule_name, status, violation_details
- **Business Rules**: Regulatory rule validation, audit trail, reporting requirements
- **Workflow**: created -> validated -> reported -> archived

## Business Requirements

### Order Management
- Support market, limit, stop orders
- Real-time order status updates
- Order modification and cancellation
- Trade execution and settlement

### Risk Management
- Pre-trade risk checks
- Position limits monitoring
- Exposure calculations
- Real-time risk alerts

### Compliance
- Regulatory rule validation
- Best execution monitoring
- Trade reporting
- Audit trail maintenance

### Portfolio Management
- Real-time position tracking
- P&L calculation
- Performance attribution
- Risk metrics calculation

### Market Data
- Real-time price feeds
- Historical data storage
- Data quality validation
- Multiple data sources support
