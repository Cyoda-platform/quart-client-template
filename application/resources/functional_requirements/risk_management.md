# Risk Management System - Functional Requirements

## High-level Goals

1. Credit Scoring: Provide an automated credit scoring pipeline that ingests customer financial data and outputs a credit score along with explainability signals and confidence metrics.
2. Fraud Detection: Detect and flag potential fraudulent transactions in real-time using rule-based checks and ML models, producing alerts and cases for investigation.
3. AML Compliance: Screen transactions and customers against watchlists and sanctions lists, escalating matches to an AML case management workflow.
4. Stress Testing: Simulate economic scenarios to assess portfolio-level credit risk and capital adequacy under stress.
5. Real-time Monitoring: Monitor data pipelines, model drift, alert volume, and system health with dashboards and alerting.

## Components

- Ingestion Layer: Collect customer, account, and transaction data from batch and streaming sources.
- Feature Store: Derived features for scoring and fraud detection.
- Model Serving: Credit scoring and fraud detection models with A/B testing capability.
- Rule Engine: Deterministic rules for quick blocking/flagging.
- AML Screening: Name-matching, sanctions list screening, and PEP checks.
- Case Management: Workflow for investigating alerts and AML matches.
- Monitoring & Observability: Metrics, logs, dashboards, and alerting.

## Detailed Functional Requirements

### 1) Credit Scoring
- FR-CS-01: System shall compute a credit score (0-850) for each customer when a scoring event occurs.
- FR-CS-02: System shall store score snapshots in CreditAccount.credit_score_snapshot with timestamp and feature contributions.
- FR-CS-03: System shall produce explainability output: top features and contribution percentages.
- FR-CS-04: Scores with confidence below threshold shall route to manual review.
- Acceptance Criteria:
  - Score values in range 0-850
  - Explainability generated for 95% of scored customers

### 2) Fraud Detection
- FR-FD-01: System shall evaluate every transaction with a set of deterministic rules and an ML fraud score.
- FR-FD-02: Transactions exceeding risk thresholds shall create an Alert and start the FraudDetectionWorkflow.
- FR-FD-03: System shall support real-time streaming evaluation with sub-second latency targets.
- Acceptance Criteria:
  - False-positive rate below configured threshold in test dataset
  - Latency within SLA for streaming paths

### 3) AML Compliance
- FR-AML-01: System shall run name and identifier screening on customers and transactions against watchlists.
- FR-AML-02: Matches above a risk threshold shall create an AML case and route to AMLCaseManagementWorkflow.
- FR-AML-03: Case investigators shall be able to annotate, escalate, and close cases.

### 4) Stress Testing
- FR-ST-01: System shall allow running scenario-based stress tests on portfolio data.
- FR-ST-02: Results must include portfolio loss estimates, sensitivity analysis, and recommended capital buffers.

### 5) Real-time Monitoring
- FR-MON-01: System shall expose metrics for model performance, alert counts, pipeline latency, and resource usage.
- FR-MON-02: Anomalies in model drift or alert volumes shall trigger monitoring alerts.

## Data Flows
1. On ingestion of transaction: enrich with customer/account data → feature computation → fraud rule evaluation & ML scoring → if flagged create Alert & start FraudDetectionWorkflow.
2. On scoring request: gather features → call credit scoring model → save snapshot → if low confidence send to manual review.
3. On AML screening hit: create AML case → route to AMLCaseManagementWorkflow.

## Test Cases
- TC-01: Create customer with synthetic profile, run scoring, assert score within expected bounds and explainability output.
- TC-02: Generate known fraudulent transaction pattern, assert Alert created and workflow triggered.
- TC-03: Run watchlist match scenario, assert AML case created and assigned.

## Non-functional Requirements
- NFR-01: System shall process 10,000 transactions/sec for streaming ingestion (scalable horizontally).
- NFR-02: Model scoring latency < 200ms for real-time APIs.
- NFR-03: Data retention and audit logs must support 7 years of records for AML compliance.

## Acceptance and Deployment
- The application will be deployed to a dev environment for integration testing.
- Observability dashboards and alerts must be configured before production rollout.
