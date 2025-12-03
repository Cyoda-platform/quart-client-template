# Real-Time Trading Platform - Functional Requirements

## Overview
This document defines the functional requirements for a real-time trading platform built on the Cyoda framework. The platform supports market data feeds, order management, portfolio tracking, risk controls, and regulatory compliance for equities and derivatives.

## Core Entities

### 1. Instrument Entity
**Purpose**: Represents tradeable securities (equities, derivatives)

**Fields**:
- `symbol`: Unique trading symbol (e.g., "AAPL", "SPY")
- `name`: Full instrument name
- `instrument_type`: EQUITY, OPTION, FUTURE, BOND
- `exchange`: Trading exchange (NYSE, NASDAQ, CME, etc.)
- `currency`: Trading currency (USD, EUR, etc.)
- `is_active`: Whether instrument is actively traded
- `contract_details`: For derivatives (strike, expiry, etc.)

**Workflow States**: initial_state -> active -> suspended -> delisted
**Processors**: InstrumentValidationProcessor
**Criteria**: InstrumentActivationCriterion

### 2. MarketData Entity
**Purpose**: Real-time market data feeds with price and volume information

**Fields**:
- `symbol`: Instrument symbol
- `price`: Current market price
- `bid_price`: Best bid price
- `ask_price`: Best ask price
- `volume`: Trading volume
- `timestamp`: Data timestamp
- `exchange`: Source exchange
- `data_quality`: GOOD, STALE, SUSPECT

**Workflow States**: initial_state -> received -> validated -> published -> archived
**Processors**: MarketDataValidationProcessor, MarketDataPublishProcessor
**Criteria**: MarketDataQualityCriterion

### 3. Order Entity
**Purpose**: Trading orders with complete lifecycle management

**Fields**:
- `order_id`: Unique order identifier
- `symbol`: Instrument symbol
- `side`: BUY, SELL
- `order_type`: MARKET, LIMIT, STOP
- `quantity`: Order quantity
- `price`: Order price (for limit orders)
- `portfolio_id`: Associated portfolio
- `trader_id`: Trader identifier
- `time_in_force`: DAY, GTC, IOC, FOK

**Workflow States**: initial_state -> pending -> validated -> submitted -> filled -> cancelled
**Processors**: OrderValidationProcessor, OrderExecutionProcessor, OrderRiskProcessor
**Criteria**: OrderRiskCriterion, OrderComplianceCriterion

### 4. Position Entity
**Purpose**: Current holdings in instruments with P&L tracking

**Fields**:
- `portfolio_id`: Associated portfolio
- `symbol`: Instrument symbol
- `quantity`: Current position size
- `average_price`: Average cost basis
- `market_value`: Current market value
- `unrealized_pnl`: Unrealized profit/loss
- `realized_pnl`: Realized profit/loss

**Workflow States**: initial_state -> open -> updated -> closed
**Processors**: PositionUpdateProcessor, PositionPnLProcessor
**Criteria**: PositionLimitCriterion

### 5. Portfolio Entity
**Purpose**: Collection of positions with performance tracking and risk management

**Fields**:
- `portfolio_id`: Unique portfolio identifier
- `name`: Portfolio name
- `trader_id`: Portfolio owner
- `total_value`: Total portfolio value
- `cash_balance`: Available cash
- `total_pnl`: Total profit/loss
- `risk_metrics`: Risk measurements

**Workflow States**: initial_state -> active -> suspended -> closed
**Processors**: PortfolioUpdateProcessor, PortfolioRiskProcessor
**Criteria**: PortfolioRiskCriterion

### 6. RiskControl Entity
**Purpose**: Risk limits and monitoring for positions and portfolios

**Fields**:
- `control_id`: Unique risk control identifier
- `entity_type`: PORTFOLIO, POSITION, ORDER
- `entity_id`: Associated entity ID
- `risk_type`: POSITION_LIMIT, VAR_LIMIT, CONCENTRATION_LIMIT
- `limit_value`: Risk limit threshold
- `current_value`: Current risk exposure
- `breach_status`: OK, WARNING, BREACH

**Workflow States**: initial_state -> active -> breached -> resolved
**Processors**: RiskMonitoringProcessor, RiskBreachProcessor
**Criteria**: RiskLimitCriterion

### 7. ComplianceCheck Entity
**Purpose**: Regulatory compliance validation and reporting

**Fields**:
- `check_id`: Unique compliance check identifier
- `rule_type`: POSITION_LIMIT, TRADING_HALT, WASH_SALE
- `entity_type`: ORDER, POSITION, PORTFOLIO
- `entity_id`: Associated entity ID
- `status`: PASS, FAIL, PENDING
- `violation_details`: Details of any violations

**Workflow States**: initial_state -> pending -> checked -> approved -> rejected
**Processors**: ComplianceValidationProcessor, ComplianceReportingProcessor
**Criteria**: ComplianceRuleCriterion

## Business Rules

### Order Management
1. All orders must pass risk checks before submission
2. Orders must comply with regulatory rules
3. Market orders execute immediately, limit orders wait for price
4. Position limits must not be exceeded

### Risk Management
1. Portfolio VAR limits must be monitored continuously
2. Position concentration limits apply per instrument
3. Risk breaches trigger immediate alerts and potential position closure

### Compliance
1. All trades must be checked against regulatory rules
2. Position limits per regulation must be enforced
3. Wash sale rules must be validated
4. Trading halts must be respected

### Market Data
1. Stale data (>5 seconds) must be flagged
2. Price movements >10% must be validated
3. Volume spikes must be monitored

## Integration Points
- Real-time market data feeds
- Order execution systems
- Risk management systems
- Regulatory reporting systems
- Portfolio management systems
