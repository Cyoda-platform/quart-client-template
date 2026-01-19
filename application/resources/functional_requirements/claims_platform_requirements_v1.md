# Insurance Claims Management Platform - Functional Requirements (v1)

Project profile: Retail — Personal lines (auto, home)
Processing model: Manual triage (human reviewers handle most decisions)

## Overview
Build an insurance claims management platform to support personal lines (auto and home) with a strong consumer UX and moderate claim volume. The platform should enable claim submission, document management, manual triage workflows, integrated communications, and tracking for claimants and staff. The repository serves as the single source of truth for this project.

## Functional Requirements

1. Claim Intake & Submission
   - Web and mobile-friendly claim submission form capturing claimant details, policy number, incident details, date/time, location, and initial damage description.
   - Allow upload of multiple documents and images (photos, police reports) with client-side validation (file types and sizes).
   - Provide real-time form validation and a progress indicator for multi-step submissions.

2. Document Management
   - Store uploaded documents associated with a claim; support previewing images and PDFs in the UI.
   - Generate and store derived thumbnails for images.
   - Support batch download of claim documents for adjusters.

3. Manual Triage & Assignment
   - Claims are queued for human triage by claims handlers.
   - Manual assignment to adjusters with assignment history tracking.
   - Configurable queues by claim type, severity, or region.

4. Case Management & Notes
   - Case timeline with events (submission, document uploads, status changes, notes).
   - Internal notes and claimant communications logging with privacy controls.

5. Automated Validations
   - Built-in validations: policy existence, coverage checks, mandatory fields, consistency checks (e.g., claim date vs. policy term).
   - Flag claims with missing or inconsistent data for manual review.

6. Fraud Detection (Basic)
   - Basic rules-based fraud detection: duplicate claim detection (same claimant/policy/date/location), suspicious document metadata.
   - Mark claims as "Requires Fraud Review" for human investigation.

7. Notifications & Communications
   - Email notifications for claim submission, assignment, and status changes.
   - In-app notifications for adjusters and claims handlers.

8. Claims Tracking & Reporting
   - Claim status (Submitted, In Review, Assigned, In Assessment, Requires Fraud Review, Approved, Denied, Settled).
   - Dashboard for operational metrics: queue sizes, average time to triage, claims by status, SLA breaches.

9. Security & Audit
   - Role-based access control (Claimant, Adjuster, Claims Handler, Admin).
   - Audit logs for key actions (status changes, assignments, note edits).

10. Integrations
   - API endpoints for claim submission and status query for partners and mobile apps.
   - Connectors for document storage and email delivery.

## Non-Functional Requirements
- Scalability: handle moderate volume with scale-to-demand for document storage and processing.
- Availability: 99.9% for the claims intake APIs.
- Data retention and compliance: support configurable retention policies and export for audits.

## Acceptance Criteria (High-level)
- End-to-end claim submission from web where a user can upload documents and receive a claim ID.
- Claims appear in the triage queue and can be assigned to an adjuster.
- Documents are stored and previewable.
- Basic fraud rules flag suspicious claims.

## Next Steps
- Define entities (Claim, Policy, Document, User, Queue, FraudAlert).
- Design triage and assignment workflows.
- Implement API contract for claim submission.

