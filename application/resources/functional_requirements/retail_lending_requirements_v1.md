# Retail Lending — Functional Requirements (v1)

## Overview
A Retail Lending Risk Management System focused on consumer credit and scoring using traditional credit bureau data and explainable scorecard models.

## Goals
- Provide reliable, explainable credit scores for new and existing retail customers
- Offer portfolio-level risk analytics and concentration monitoring
- Support stress testing for macroeconomic scenarios
- Provide regulatory-ready reporting (e.g., Basel/IFRS alignment)
- Real-time decisioning hooks for pre-approval and fraud checks

## Functional Requirements

1. Data Ingestion
   - Ingest customer and credit bureau data (standard formats: CSV, JSON, API) with validation and lineage.
   - Store raw ingestion artifacts for audit and reprocessing.

2. Feature Engineering
   - Derive standard credit bureau features: recent delinquencies, utilization ratios, open accounts, age of credit, inquiries.
   - Implement monotonic transformations and binning for scorecard inputs.

3. Scorecard Modeling
   - Support logistic regression scorecards with weight-of-evidence (WoE) transformations.
   - Allow manual binning and configurable WoE tables per feature.
   - Produce per-customer score and explainability outputs (feature contributions).

4. Decisioning Engine
   - Rule-based approval/decline flows using score thresholds and business rules.
   - Support manual overrides and case management flags.

5. Portfolio Analytics
   - Calculate vintage analysis, delinquency curves, PD/LGD/EAD rollups, and exposure concentration metrics.
   - Provide time-series dashboards and exportable reports.

6. Stress Testing
   - Apply macroeconomic scenarios to scorecard PDs and run portfolio-level loss projections.
   - Allow scenario builders and scenario templates.

7. Reporting & Compliance
   - Generate regulatory reports and maintain audit trails for data and model versions.
   - Version-controlled artifacts stored in the repository.

8. Monitoring & Alerts
   - Real-time monitoring for data drift, population shift, model performance degradation.
   - Alerting hooks for SLA breaches and model retraining triggers.

9. Security & Access Control
   - Role-based access control for model artifacts, data exports, and admin functions.

10. Extensibility
    - Pluggable model backends (scikit-learn, statsmodels) and clear adapters for future ML models.

## Non-functional Requirements
- Data retention & lineage for at least 7 years
- 99.9% availability for scoring API
- Latency: <200ms for scoring in pre-approval flow (target)
- Explainability: Provide per-feature contribution for each decision

## Acceptance Criteria
- Ability to score a batch of 100k customers end-to-end from ingestion to scoring
- Scorecard model with WoE transforms and explainability validated on a test fold
- Dashboard showing portfolio vintage and delinquency rates

## Next Steps
- Define Entities (Customer, CreditBureauReport, Scorecard, Portfolio, Scenario)
- Design Workflows (Ingestion -> Feature Engineering -> Scoring -> Monitoring)
- Implement initial scorecard model and a scoring API

