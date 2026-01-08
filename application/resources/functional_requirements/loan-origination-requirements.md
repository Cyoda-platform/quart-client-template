# Loan Origination & Management System - Functional Requirements

## Overview
A fully automated Loan Origination and Management System (LOMS) focused on US regulatory (SEC-level) controls. The system handles application intake, automated credit assessment and decisioning, disbursement tracking, repayment scheduling, default management, regulatory reporting, and comprehensive audit trails.

## Core Capabilities

1. Application Intake
- Web/API-based application intake for consumer and small business loans.
- KYC collection: identity documents, SSN/TIN, address, employment, income verification.
- Document upload with virus scan and OCR extraction.
- Real-time identity verification integration.

2. Automated Credit Assessment & Decisioning
- Configurable decision engine combining rule-based checks and machine learning risk scores.
- Instant eligibility checks, debt-to-income ratio, credit bureau integration (pull reports), fraud detection signals.
- Decision outcomes: Approve, Conditional Approve (require additional verification or collateral), Decline.
- Automated offer generation with interest rate, term, fees, and prepayment penalties.

3. Disbursement Tracking
- Track disbursement status: Pending, Approved for Disbursement, Disbursed, Failed.
- Integration with payment rails to initiate transfers and reconcile settlements.
- Support for partial disbursements and scheduled disbursements.

4. Repayment Scheduling & Management
- Amortization schedule generation (fixed, interest-only, balloon) with support for early repayments.
- Automatic payment collection via ACH and card (vaulted tokens) with retry logic.
- Grace periods, late fee calculation, and interest accrual.

5. Default Management & Collections
- Automated delinquency detection based on scheduled payments and account balance.
- Escalation workflows: reminders, soft collections, hard collections, charge-off.
- Support for settlement offers, hardship programs, and repossession processes where applicable.

6. Regulatory Compliance & Reporting
- Comprehensive audit logs for all decisions, data access, and configuration changes.
- SEC-style reporting: transaction trails, exceptions, and supervisory approvals.
- Data retention and e-discovery support; encryption at rest and in transit.

7. Security & Data Privacy
- Role-based access control (RBAC), SSO integration (SAML/OIDC), multi-factor authentication.
- PII redaction in logs, consent management, and breach notification workflows.

8. Observability & Monitoring
- Metrics for application throughput, decision latency, default rates, and portfolio health.
- Alerts and dashboards for operational and compliance teams.

## Non-Functional Requirements
- Availability: 99.9% SLA for core decisioning and disbursement services.
- Performance: median decision latency under 2 seconds for standard applications.
- Scalability: auto-scale to handle peak loads (e.g., batch onboarding).
- Maintainability: infrastructure-as-code and GitOps-driven deployments.

## Acceptance Criteria
- Successful end-to-end flow from application to disbursement in staging with test credit bureau stubs.
- Traceable audit logs for 100% of automated decisions and manual overrides.
- Regulatory report generation for a given period with filters on exceptions and manual reviews.

## Out of Scope
- International disbursements and non-US regulatory frameworks.

## Next Steps
- Define domain entities (Applicant, Loan, CreditProfile, Decision, Disbursement, PaymentSchedule, ChargeOff).
- Design workflows for ApplicationProcessing, CreditDecisioning, Disbursement, RepaymentProcessing, and Collections.
- Generate initial entity and workflow artifacts from these requirements.
