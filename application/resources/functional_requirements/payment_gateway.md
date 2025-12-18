# Payment Gateway — Functional & Non-Functional Requirements

## Overview
This document describes the functional and non-functional requirements for a payment gateway that supports:
- Multi-currency processing
- Integrated fraud detection and risk scoring
- PCI-compliant architecture and card data handling
- Recurring billing and subscription management
- Real-time transaction monitoring, alerting, and observability

The goal is to provide a secure, reliable, auditable platform for processing payments for merchants while minimizing fraud, reducing PCI scope, supporting subscriptions, and providing operational visibility.

## Scope
In scope:
- Accepting card and tokenized payments across multiple currencies
- Merchant management and onboarding metadata
- Subscription lifecycle, recurring invoice generation and billing
- Real-time fraud scoring and rule-based actions (accept, challenge, decline)
- Transaction routing, settlement batches, and reconciliation events
- Metrics, dashboards, and alerting for transaction and system health

Out of scope (for initial MVP):
- Building direct integrations with card networks; instead provide standardized adapter interfaces for connectors
- Printing physical receipts, point-of-sale hardware integration

## Stakeholders
- Product owners and merchant integrators
- Fraud analysts and risk operations
- Platform reliability engineers and SREs
- Compliance officers (PCI)

---

## Functional Requirements

1. Payments & Multi-Currency
- FR-01: The gateway MUST accept payment requests with a currency code (ISO 4217) and amount.
- FR-02: The gateway MUST support merchant-level settlement currency configuration (merchant can have a settlement currency independent of payment currency).
- FR-03: The gateway MUST record the original payment currency, exchange rate used, and equivalent settlement amount for reconciliation.
- FR-04: The gateway MUST support card tokenization to minimize sensitive data storage.
- FR-05: The gateway MUST expose APIs for: Create Payment, Capture, Refund, Void, and Retrieve Payment.

2. Payment Flows
- FR-06: Support both immediate-authorization (authorize and capture) and delayed capture flows.
- FR-07: Support saved customer payment methods and one-time payments.
- FR-08: Support 3-D Secure / challenge flows as a challenge action triggered by fraud scoring (abstract flow; implementation plugs into challenge provider).

3. Recurring Billing & Subscriptions
- FR-09: Support subscription objects with plan definitions (price, currency, billing interval, trial period, prorations).
- FR-10: Automatically generate invoices and attempt scheduled charges based on subscription billing cycles.
- FR-11: Implement retry and dunning policies configurable per merchant (e.g., retry up to N times with exponential backoff, notify merchant/customer).
- FR-12: Support upgrade/downgrade of plans with proration calculations.

4. Fraud Detection & Risk Management
- FR-13: Every payment request MUST be scored with a fraud risk score and a recommended action (ALLOW, REVIEW, DECLINE).
- FR-14: The platform MUST support both a rules engine (configurable rules) and a machine learning risk score integration (pluggable service).
- FR-15: Allow merchant-specific risk policies and thresholds.
- FR-16: Capture risk signals and provide an audit trail for any automated actions or overrides.

5. PCI Compliance & Sensitive Data Handling
- FR-17: The gateway MUST avoid storing raw PANs. Card data must be tokenized at ingestion or not persisted.
- FR-18: Use in-transit and at-rest encryption for any sensitive data. Key management MUST be auditable.
- FR-19: Maintain detailed audit logs for all payment lifecycle events and administrative actions for compliance reviews.
- FR-20: Support secure export of logs and reporting required for compliance audits for defined retention periods.

6. Settlement & Reconciliation
- FR-21: Emit settlement events at merchant-configured intervals (daily, hourly) with per-transaction settlement mapping.
- FR-22: Provide reconciliation endpoints and reports that include original currency, settlement currency, exchange rates, fees, and net amounts.

7. Real-time Monitoring & Alerts
- FR-23: Produce real-time transaction metrics (TPS, success rate, median latency, error rate) and per-merchant metrics.
- FR-24: Generate alerts for anomaly detection (e.g., spike in declines, unusual volume) and critical system outages.
- FR-25: Provide dashboards for fraud analysts and operations with drill-down per transaction including full risk signal context.

8. APIs & Webhooks
- FR-26: Provide RESTful APIs for all payment and subscription operations, and webhooks for asynchronous events (payment.succeeded, payment.failed, subscription.renewed, dispute.created).
- FR-27: Webhook signing mechanism for authenticity verification.

9. Administrative & Onboarding
- FR-28: Merchant onboarding metadata and KYC fields for compliance reviews.
- FR-29: Role-based access control for platform users (admin, risk_analyst, support, read-only).

---

## Non-Functional Requirements

1. Security & Compliance
- NFR-01: Data-in-transit MUST be encrypted using strong TLS.
- NFR-02: Keys and secrets MUST be stored in a secure key management system with access controls and audit trails.
- NFR-03: Audit logs MUST be tamper-evident and retained for configurable periods (default 1 year).

2. Performance & Scalability
- NFR-04: The gateway MUST support burst traffic and scale horizontally.
- NFR-05: Typical transaction latency (authorization path) SHOULD be under 300ms median for common flows; percentiles depend on external connector latency.
- NFR-06: The system SHOULD handle at least 1,000 TPS in scale-out configurations for medium-sized merchants (targets defined per merchant tier).

3. Reliability & Availability
- NFR-07: Target platform availability for payment processing APIs SHOULD be 99.95% (SLA to be negotiated per merchant tier).
- NFR-08: Support graceful degradation for non-critical components (analytics, reporting) while maintaining core authorization paths.

4. Observability & Monitoring
- NFR-09: Emit structured traces, metrics, and logs for transactions. Traces SHOULD include payment_id, merchant_id, and correlation ids.
- NFR-10: Provide dashboards and alerting for operational SLO breaches and fraud spikes.

5. Data Retention & Privacy
- NFR-11: Support configurable retention windows for transaction data and logs per merchant and compliance requirements.
- NFR-12: Support data export and erasure requests to satisfy privacy and compliance needs.

---

## Acceptance Criteria
- AC-01: Process a payment in EUR and settle to a merchant configured to receive USD; settlement report must include exchange rate and net amount.
- AC-02: A subscription with monthly billing and a trial period must correctly charge at the end of the trial and handle failed payments per retry policy.
- AC-03: Fraud rules can be configured to auto-decline payments above a score threshold and send declined webhooks.
- AC-04: No raw PAN values are present in persisted storage for test transactions that use tokenization.
- AC-05: Real-time dashboards must show per-minute TPS and alert on anomalous decline rate increases.

---

## API Surface (high level)
- POST /payments — Create a payment (body: amount, currency, payment_method, customer_id, merchant_id, metadata)
- POST /payments/{id}/capture — Capture an authorized payment
- POST /payments/{id}/refund — Refund a payment
- GET /payments/{id} — Retrieve payment status and audit trail
- POST /subscriptions — Create subscription
- POST /subscriptions/{id}/cancel — Cancel subscription
- GET /reports/settlement — Retrieve settlement reports

---

## Notes for Design Phase (Entities & Workflows)
- Entities to model: Merchant, Customer, PaymentMethod (token), Payment/Transaction, Subscription, Invoice, FraudAlert, SettlementBatch
- Workflows to model: PaymentProcessing (authorize -> score -> capture/decline), RecurringBilling (invoice generation -> attempt charge -> retry/dunning), FraudDetection (score -> action -> manual review), Settlement/Reconciliation

---

## Next Steps
1. Define concrete entities (JSON instances) for the recommended entities above.
2. Define the PaymentProcessing and RecurringBilling workflows in Canvas and validate them against the workflow schema.
3. Generate code (incremental or full application) and start environment provisioning in parallel.

