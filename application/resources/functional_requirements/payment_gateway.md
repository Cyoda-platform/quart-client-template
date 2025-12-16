# Payment Gateway - Functional Requirements

## Overview
A payment gateway service to process payments for merchants. Core features:
- Multi-currency support (accept and settle in multiple currencies)
- Fraud detection and prevention
- PCI-compliant card handling and vaulting (minimal scope: do not store raw PAN)
- Recurring billing and subscription management
- Real-time transaction monitoring and alerts

## Actors
- Merchant (system integrating with the gateway)
- Customer (payer)
- Gateway Admin (operations team)
- External Payment Networks / Acquirers
- Fraud Service (internal and/or third-party)

## High-level Use Cases
1. One-time payment processing (card, wallet, bank transfer)
2. Recurring billing / subscription lifecycle (create, bill, retry, cancel)
3. Multi-currency capture/conversion and settlement
4. Fraud scoring and blocking for risky transactions
5. Tokenization / secure card storage (PCI scope reduction)
6. Real-time monitoring, dashboards, and alerting for failed or suspicious activity

## Functional Requirements
### Payments
- Accept payment requests via REST API with fields: amount, currency, payment_method (token or method details), customer_id, metadata.
- Support common payment methods: card (tokenized), ACH/bank transfer, popular wallets.
- Validate currency and amount; return clear error codes for invalid requests.
- Perform authorization and capture flows (authorize-only, authorize+capture).
- Provide idempotency key support for safe retries.

### Multi-currency
- Accept and process payments in customer-facing currencies.
- Support merchant settlement currency configuration; include conversion pipelines where required.
- Store currency on transaction records and apply exchange rates (external rate provider integration). Maintain audit trail for conversion rates used.

### Recurring Billing / Subscriptions
- Create subscription objects tied to customer and plan (plan: price, currency, billing_interval).
- Schedule billing triggers and process charges automatically.
- Handle failed payments with configurable retry/backoff policies and notify merchant.
- Allow plan upgrades/downgrades and pro-rated billing.

### Fraud Detection
- Integrate with a fraud scoring system (internal rules + third-party scoring API).
- On transaction request, compute fraud score and apply rules: accept, challenge, or block.
- Flag high-risk transactions for manual review and route to a review queue.
- Maintain a history of fraud decisions for auditing and model feedback.

### PCI Compliance & Security
- Never persist raw PAN in application storage. Use tokenization or vault service for card data.
- All card collection points must be PCI SAQ A friendly (hosted fields or direct tokenization).
- Encrypt sensitive fields at rest and use TLS in transit.
- Implement role-based access controls for admin operations and audit logging for sensitive actions.
- Support secure key rotation and vault integrations for secrets management.

### Real-time Monitoring & Alerts
- Emit events for key transactions (payment.created, payment.succeeded, payment.failed, subscription.renewed, fraud.flagged).
- Provide an events stream consumed by the monitoring subsystem for dashboarding and alerts.
- Support thresholds and alerting (e.g., sudden surge in failures, high-value blocked transactions).
- Provide metrics: TPS, success rate, error rate, fraud rate, average latency, SLA alerts.

## APIs
- Transaction API: POST /payments (create), GET /payments/{id} (retrieve), POST /payments/{id}/capture, POST /payments/{id}/refund
- Subscription API: POST /subscriptions, GET /subscriptions/{id}, POST /subscriptions/{id}/cancel
- Webhooks: Provide webhook endpoints for merchant callbacks on payment events
- Admin APIs: transaction search, risk reports, manual review actions

## Events & Data Model (summary)
- Payment: id, merchant_id, customer_id, amount, currency, status, method_token, fraud_score, created_at, processed_at
- Subscription: id, customer_id, plan_id, status, next_billing_date
- Customer: id, email, name, default_payment_token

## Non-Functional Requirements
- Availability: 99.9% for transaction processing APIs
- Latency: < 300ms median processing time for simple auth flows (no external conversion)
- Scalability: Horizontal scaling for event processors and web/API layers
- Auditability: Retain transaction and fraud decision logs for at least 2 years
- Compliance: Meet PCI DSS requirements for card data handling (scope reduction by tokenization)

## Acceptance Criteria
- Able to process multi-currency payment requests end-to-end in a test environment
- Tokenization flow implemented and verified (no PAN stored)
- Subscription creation and automatic billing run for scheduled intervals
- Fraud scoring integrated and rule-based blocking demonstrated
- Transaction events emitted and visible in monitoring dashboards

## Implementation Considerations (Design notes)
- Use event-driven architecture: capture events to a durable event store or message bus
- Separate processors for payments, subscriptions, fraud, and reconciliation
- External integrations: payment networks, currency rate provider, fraud scoring API
- Provide a sandbox mode and test keys for merchant integration testing

## Next Steps (Cyoda Journey)
1. Design entities and workflows in Canvas (payments, subscriptions, customers, fraud_review)
2. Generate the application code from these requirements (Build)
3. Provision a Cyoda environment and deploy the app (Environment → Deploy)

