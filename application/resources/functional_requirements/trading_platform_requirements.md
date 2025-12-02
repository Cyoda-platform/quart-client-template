# Real-Time Trading Platform Requirements

## Overview
Build a comprehensive real-time trading platform with market data feeds, order management, portfolio tracking, risk controls, and regulatory compliance for equities and derivatives.

## Core Entities and Requirements

### 1. MarketData Entity
**Purpose**: Real-time market data feeds with price, volume, and market status tracking

**Fields**:
- symbol: string (required) - Trading symbol (e.g., "AAPL", "SPY")
- instrument_type: string (required) - "EQUITY" or "DERIVATIVE"
- price: number (required) - Current market price
- bid_price: number (optional) - Best bid price
- ask_price: number (optional) - Best ask price
- volume: number (required) - Trading volume
- market_status: string (required) - "OPEN", "CLOSED", "PRE_MARKET", "AFTER_HOURS"
- timestamp: string (required) - Data timestamp
- exchange: string (required) - Exchange identifier

**Workflow**: initial_state -> validated -> enriched -> published
**Processors**: MarketDataValidationProcessor, MarketDataEnrichmentProcessor
**Criteria**: MarketDataValidationCriterion

### 2. Instrument Entity
**Purpose**: Financial instruments (equities and derivatives) with trading parameters

**Fields**:
- symbol: string (required) - Trading symbol
- instrument_type: string (required) - "EQUITY" or "DERIVATIVE"
- name: string (required) - Full instrument name
- exchange: string (required) - Primary exchange
- currency: string (required) - Trading currency
- lot_size: number (required) - Minimum trading unit
- tick_size: number (required) - Minimum price increment
- is_tradable: boolean (required) - Trading status
- contract_specs: object (optional) - Derivative contract specifications

**Workflow**: initial_state -> validated -> active
**Processors**: InstrumentSetupProcessor
**Criteria**: InstrumentValidationCriterion

### 3. Order Entity
**Purpose**: Order lifecycle management with execution tracking

**Fields**:
- order_id: string (required) - Business order identifier
- symbol: string (required) - Trading symbol
- order_type: string (required) - "MARKET", "LIMIT", "STOP", "STOP_LIMIT"
- side: string (required) - "BUY" or "SELL"
- quantity: number (required) - Order quantity
- price: number (optional) - Limit/stop price
- filled_quantity: number (default: 0) - Executed quantity
- remaining_quantity: number - Remaining quantity
- portfolio_id: string (required) - Associated portfolio
- time_in_force: string (required) - "DAY", "GTC", "IOC", "FOK"

**Workflow**: initial_state -> validated -> risk_checked -> submitted -> filled/cancelled
**Processors**: OrderValidationProcessor, RiskCheckProcessor, OrderExecutionProcessor
**Criteria**: OrderValidationCriterion, RiskCheckCriterion

### 4. Portfolio Entity
**Purpose**: Position tracking and P&L calculations

**Fields**:
- portfolio_id: string (required) - Business portfolio identifier
- account_id: string (required) - Account identifier
- cash_balance: number (required) - Available cash
- total_value: number (required) - Total portfolio value
- unrealized_pnl: number (default: 0) - Unrealized P&L
- realized_pnl: number (default: 0) - Realized P&L
- positions: array (default: []) - Current positions

**Workflow**: initial_state -> active -> updated
**Processors**: PortfolioUpdateProcessor, PnLCalculationProcessor
**Criteria**: PortfolioValidationCriterion

### 5. Trade Entity
**Purpose**: Executed transactions with settlement tracking

**Fields**:
- trade_id: string (required) - Business trade identifier
- order_id: string (required) - Originating order ID
- symbol: string (required) - Trading symbol
- side: string (required) - "BUY" or "SELL"
- quantity: number (required) - Executed quantity
- price: number (required) - Execution price
- portfolio_id: string (required) - Associated portfolio
- execution_time: string (required) - Execution timestamp
- settlement_date: string (required) - Settlement date

**Workflow**: initial_state -> validated -> settled -> reported
**Processors**: TradeSettlementProcessor, TradeReportingProcessor
**Criteria**: TradeValidationCriterion

### 6. RiskControl Entity
**Purpose**: Pre-trade risk checks and exposure monitoring

**Fields**:
- rule_id: string (required) - Risk rule identifier
- rule_type: string (required) - "POSITION_LIMIT", "EXPOSURE_LIMIT", "CONCENTRATION_LIMIT"
- portfolio_id: string (required) - Associated portfolio
- symbol: string (optional) - Specific symbol (if applicable)
- limit_value: number (required) - Risk limit value
- current_value: number (required) - Current exposure/position
- is_breached: boolean (default: false) - Breach status
- breach_threshold: number (required) - Warning threshold

**Workflow**: initial_state -> active -> monitored
**Processors**: RiskMonitoringProcessor, RiskAlertProcessor
**Criteria**: RiskLimitCriterion

### 7. Compliance Entity
**Purpose**: Regulatory reporting and audit trails

**Fields**:
- report_id: string (required) - Business report identifier
- report_type: string (required) - "TRADE_REPORT", "POSITION_REPORT", "RISK_REPORT"
- portfolio_id: string (required) - Associated portfolio
- reporting_date: string (required) - Report date
- data: object (required) - Report data
- status: string (required) - "PENDING", "SUBMITTED", "ACKNOWLEDGED", "REJECTED"
- submission_time: string (optional) - Submission timestamp

**Workflow**: initial_state -> validated -> submitted -> acknowledged
**Processors**: ComplianceValidationProcessor, ComplianceSubmissionProcessor
**Criteria**: ComplianceValidationCriterion

## Business Rules

### Order Management
- Orders must pass risk checks before submission
- Market orders execute immediately at market price
- Limit orders execute only at specified price or better
- Stop orders become market orders when triggered

### Risk Management
- Position limits must be enforced before order execution
- Exposure limits calculated in real-time
- Risk breaches trigger immediate alerts and order blocks

### Portfolio Management
- Positions updated in real-time with trade executions
- P&L calculated using mark-to-market pricing
- Cash balances adjusted with trade settlements

### Compliance
- All trades must be reported within regulatory timeframes
- Audit trails maintained for all transactions
- Position reports generated daily

## API Endpoints Required
- CRUD operations for all entities
- Real-time market data streaming
- Order submission and management
- Portfolio position queries
- Risk monitoring dashboards
- Compliance reporting
