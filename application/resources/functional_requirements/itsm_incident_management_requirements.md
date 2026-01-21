# ITSM / Incident Management - Functional Requirements

Profile: Standard SLA — 24h response / 72h resolution

Included features:
- Ticket lifecycle & statuses (NEW, IN_PROGRESS, RESOLVED, CLOSED, REOPENED)
- Role-based assignment & escalation (L1, L2, Manager roles; manual and automated assignment rules)
- SLA tracking & alerts (response and resolution timers, SLA breach notifications, reporting)
- Email notifications & templating (templates for assignment, resolution, escalation)

Functional requirements:
1. Ticket creation: System shall allow creating tickets with title, description, reporter, priority, attachments, and optional metadata.
2. Ticket lifecycle: Tickets progress through statuses: NEW -> IN_PROGRESS -> RESOLVED -> CLOSED. Tickets can be REOPENED which moves them back to IN_PROGRESS.
3. Assignment rules: Tickets are assigned to L1 by default; auto-escalate to L2 after configurable timeout or manual escalation.
4. SLA timers: On ticket creation, start response and resolution timers per SLA profile. System shall send alerts when response or resolution is approaching breach and on breach.
5. Notifications: Send templated emails on assignment, escalation, resolution, and closure. Support localization for templates.
6. Audit trail: Record status changes, assignee changes, comments, and SLA events for reporting and compliance.
7. Reporting: Provide dashboards for SLA compliance, ticket aging, and agent workload.

Acceptance criteria:
- Tickets can be created and traverse the lifecycle as specified.
- SLA timers trigger alerts and escalate as configured.
- Email notifications use templates and are sent at the proper lifecycle events.

Non-functional requirements:
- System should support up to 5,000 tickets/day with 99.9% uptime.
- Email delivery latency under 10 seconds for notification events.

