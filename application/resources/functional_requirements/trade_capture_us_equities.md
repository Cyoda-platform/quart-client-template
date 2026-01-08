# Trade Capture — US Equities (SEC)

## Scope
- Primary Focus: Trade capture & lifecycle (order entry)
- Supported order types: Market and Limit
- Initial scope: Full lifecycle — automated matching and settlement automation

## Functional Requirements
1. Order Entry API
   - Create orders with fields: orderId, customerId, symbol, quantity, price (nullable for market), orderType (Market|Limit), side (Buy|Sell), timestamp
   - Validate orders against trading rules and position limits

2. Order Matching Engine
   - Real-time matching engine supporting Market & Limit orders
   - Price-time priority matching
   - Partial fills and order state transitions

3. Trade Settlement
   - Automated settlement workflow post-match with reconciliation
   - Support trade lifecycle states: NEW → MATCHED → SETTLED → RECONCILED

4. Audit & Compliance
   - Immutable audit log for each order and trade event
   - Exportable reports suitable for SEC review

5. Security & Access
   - API authentication, role-based access for traders and compliance

## Non-Functional Requirements
- Low latency for order matching (sub-second for typical order volumes)
- Durable storage for orders and audit logs
- Configurable retry and reconciliation policies

## Entities (initial suggestions)
- Customer (id, name, email, phone)
- Order (orderId, customerId, symbol, quantity, price, orderType, side, status, timestamps)
- Trade (tradeId, buyOrderId, sellOrderId, price, quantity, timestamp, settlementStatus)

## Workflows (initial suggestions)
- OrderPlacement workflow: validate -> persist -> publish to matching engine
- Matching workflow: receive order -> match -> create trade -> initiate settlement
- Settlement workflow: settle -> reconcile -> archive

## Acceptance Criteria
- The system can accept and persist Market and Limit orders
- Matching engine correctly matches orders by price-time priority
- Successful automated settlement transitions matched trades to SETTLED

