# Insurance Claims Management Platform — Functional Requirements

Version: 1.0  
Branch: dc169d91-9b81-449d-804b-e16f92129e38

## 1. Purpose & Scope
Build an end-to-end insurance claims platform that enables claimants and internal staff to submit, process, investigate, settle, and track claims efficiently and transparently. V1 focuses on Property & Casualty (P&C)-style claims with extensible design for other lines.

In scope (V1):
- Claim submission (web/API), intake, validation, triage, assignment
- Document management (upload, classification, extraction, linkage to claims)
- Automated processing (rules, coverage checks, deductible application, risk scoring)
- Fraud detection (signals, thresholds, SIU queue, investigation workflow)
- Claims tracking (timeline, statuses, SLAs, notifications)
- Payments initiation and closure

Out of scope (V1):
- Complex subrogation and litigation workflows
- Multi-currency settlement complexity beyond basic configuration
- External billing/ERP integrations beyond placeholder stubs

## 2. Personas & Roles
- Claimant: Submits and tracks personal claims and documents
- Customer Service Rep (CSR): Assists claimants, updates claim info, requests documents
- Adjuster: Reviews, investigates, and adjudicates claims
- SIU/Fraud Analyst: Investigates suspected fraud cases
- Supervisor: Oversees queues, handles escalations and approvals
- Finance: Reviews and authorizes payments
- System: Executes automated rules, timers, and notifications

Role-based access (examples):
- Claimant: Read/write own claim and documents; read-only status and messages
- CSR: Read/write claims in intake/triage; request docs; limited approvals per policy
- Adjuster: Read/write assigned claims; approve/deny/partial; create tasks
- SIU: Read/write FraudCase; place holds; close with disposition
- Supervisor: Reassign, override, approve payments within threshold
- Finance: Finalize payments; reconcile and mark paid
- System: Execute automation, scoring, SLA timers

## 3. Core Entities (High-Level)
- Claim: id, policyId, claimantId, type, lossDate, reportedDate, channel, status, coverageType, deductible, claimedAmount, approvedAmount, payoutAmount, riskScore, assignee, slaDueAt
- Claimant: id, name, contact (email, phone), address, policyIds[]
- Policy: id, holderId, coverageType, coverageLimits, deductible, effectiveFrom, effectiveTo, status
- Document: id, claimId, type (ID, police report, photos, invoice, medical, other), source, filename, version, checksum, extractedFields{}
- Payment: id, claimId, amount, method, approvalChain[], status (pending, approved, sent, failed, settled), reference
- Task: id, claimId, owner, type, description, dueAt, status
- FraudCase: id, claimId, reasons[], riskScore, status (open, investigating, cleared, referred), disposition, notes[]
- Note/Message: id, claimId, author, role, content, createdAt
- AuditEvent: id, claimId, actor, action, before{}, after{}, at

Note: Entity fields are indicative; final schema will be generated from Canvas design.

## 4. Workflows (State Machines)

### 4.1 Claim Submission & Intake
States:
- Draft → Submitted → Intake → Validated → Triage → Assigned

Events/Triggers:
- SubmitClaim, UpdateClaim, AddDocument, ValidatePolicyCoverage, AutoScoreRisk, AssignAdjuster

Rules/Automation:
- On Submitted: create Intake task; required docs checklist based on claim type
- On ValidatePolicyCoverage: verify active policy, coverageType, limits, deductible
- On AutoScoreRisk: compute riskScore; if high, route to SIU Review queue
- On Triage: prioritize based on severity, riskScore, and SLA

SLAs:
- Intake within 30 minutes of submission
- Validation within 4 business hours

### 4.2 Document Management
States (per Document):
- Uploaded → Classified → Extracted → Linked → Verified

Events:
- UploadDocument, ClassifyDocument, ExtractFields, LinkToClaim, VerifyDocument, ReplaceDocument

Rules:
- Enforce allowed file types/sizes; checksum for deduplication
- Classification drives required extracted fields (e.g., invoice total, incident date)
- Versioning on replacement; maintain full audit trail

### 4.3 Automated Processing
States (automation phases within a claim):
- PreChecks → CoverageCheck → DeductibleApply → RiskScoring → AutoDecision

Rules/Behaviors:
- CoverageCheck: claimedAmount ≤ coverageLimit; policy active at lossDate
- DeductibleApply: payoutBase = max(claimedAmount - deductible, 0)
- RiskScoring: calculate riskScore (0–100) from rules; flag ≥ threshold
- AutoDecision: if low risk, within auto-approve threshold and complete docs → Approve; if mismatches or insufficient docs → ManualReview; if blatant mismatch → AutoDeny

### 4.4 Fraud Detection (SIU)
States:
- ReviewQueue → Investigating → Decisioned (Cleared | Confirmed | Referred)

Triggers:
- High riskScore, suspicious patterns, document inconsistencies, duplicate claims

Behaviors:
- Place hold on payments while under investigation
- Add notes, attach evidentiary documents, request additional info
- Feedback loop: final disposition informs future risk rules configuration

### 4.5 Manual Review & Adjustment
States:
- Assigned → InReview → InfoRequested → Decisioned (Approve | Partial | Deny) → ReadyForPayment

Behaviors:
- Create tasks, reassign, request additional documents
- Supervisor override path for edge cases

### 4.6 Payments & Closure
States:
- PendingApproval → Approved → Disbursed → Reconciled → Closed

Rules:
- Dual control for amounts over configured threshold
- Prevent disbursement when fraud hold is active
- Reconciliation event updates Payment to settled and Claim to Closed

### 4.7 Claim Tracking & Notifications
- Maintain a timeline of key events and status changes
- SLA timers for intake/validation/review/payment; reminders and escalations
- Notifications to claimant and internal roles on major transitions

## 5. Business Rules (Illustrative)
- Eligibility: policy must be active on lossDate; coverageType matches claim type
- Documentation completeness: minimal set per claim type before decision
- Deductible: apply once per claim; never yield negative payout
- Payout caps: cannot exceed coverage limit; partial approvals allowed with rationale
- Fraud flags: threshold-based (e.g., riskScore ≥ 70) or rule matches place claim in SIU queue
- Approvals: amounts > threshold require Supervisor + Finance approvals

## 6. SLAs & KPIs
SLAs:
- Intake start ≤ 30 minutes after submission
- Validation complete ≤ 4 business hours
- First Adjuster touch ≤ 8 business hours after assignment
- SIU initial review ≤ 1 business day after queueing
- Payment processing ≤ 2 business days after approval

KPIs:
- Average time per stage (intake, validation, review, payment)
- Auto-approval rate, denial rate, partial rate
- Reopen rate; SIU referral and confirmation rates
- SLA adherence; queue aging and backlog

## 7. Security, Privacy, and Audit
- Role-based access on entities and actions
- PII handling: only necessary data stored; masked views where appropriate
- Audit events for all create/update/decision actions
- Data retention: configurable retention and deletion windows per document type

## 8. Non-Functional Requirements
- Performance: typical interactions < 500ms server processing for standard operations
- Scalability: handle growth in claims volume via horizontal scaling patterns
- Reliability: graceful handling of retries and idempotent processors for events
- Observability: tasks, logs, and status dashboards for workflows and queues

## 9. Acceptance Criteria (Samples)
- A claimant can submit a claim with minimum required fields and upload documents
- Intake tasks are created automatically upon submission
- Coverage validation fails when policy is inactive or limits are exceeded
- Claims within thresholds and complete docs auto-approve; high risk routes to SIU
- Payments cannot be disbursed while SIU hold is active
- Claim timeline displays statuses and key events; notifications are sent on transitions

## 10. Test Scenarios (Samples)
1) Happy path: complete docs, valid policy, low risk → auto-approved → payment → closed
2) Missing docs: request additional info → resubmission → manual approval → payment
3) High risk: SIU queue → investigate → cleared → proceed to manual approval → payment
4) Coverage exceeded: partial approval based on limit and deductible
5) Fraud confirmed: claim denied; audit records preserved; claimant notified
6) Reopen: closed claim reopened due to new evidence → additional review path

## 11. Open Questions & Assumptions
- Thresholds for auto-approval and fraud scoring to be provided by business stakeholders
- Document types and extraction fields may expand in later versions
- Payment reconciliation details may evolve with finance policies

---
This document is intended to be reviewed and refined in Canvas. Once approved, the application will be generated from this design and prepared for deployment.
