# Functional Requirements

Version: 1.0
Last Updated: 2025-12-30
Owner: Cyoda App Team

## 1. Overview
A lightweight event-driven Task Management application to demonstrate Cyoda patterns. Users can create tasks, assign them to a teammate, track progress through states, and complete or cancel tasks. The system emits domain events for each action, enabling processors to trigger side-effects (notifications, SLA checks).

## 2. Goals
- Allow users to create, view, update, assign, complete, and cancel tasks.
- Track task lifecycle via explicit states and transitions.
- Emit domain events for each significant action for auditability and integrations.
- Provide simple APIs to drive the workflows.

## 3. Non-Goals
- Advanced project management features (sprints, epics, story points).
- Time tracking, billing, or analytics dashboards.

## 4. Personas
- Reporter: Creates tasks and monitors status.
- Assignee: Works on assigned tasks and updates progress.
- Admin: Can manage any task for support purposes.

## 5. Core Entities
- Task
  - id: UUID (string)
  - title: string (1..120)
  - description: string (0..2000)
  - priority: enum [low, medium, high]
  - reporterId: string (user id/email)
  - assigneeId: string|null
  - createdAt: ISO timestamp
  - updatedAt: ISO timestamp
  - dueAt: ISO timestamp|null
  - tags: [string]
  - state: enum [NEW, ASSIGNED, IN_PROGRESS, COMPLETED, CANCELED]

- User (lightweight reference used by IDs only)

## 6. Workflows (Task lifecycle)
Initial State: NEW

States and transitions:
- NEW
  - on assign -> ASSIGNED
  - on cancel -> CANCELED
- ASSIGNED
  - on start -> IN_PROGRESS
  - on reassign -> ASSIGNED (self transition with new assignee)
  - on cancel -> CANCELED
- IN_PROGRESS
  - on complete -> COMPLETED
  - on pause -> ASSIGNED
  - on cancel -> CANCELED
- COMPLETED (terminal)
- CANCELED (terminal)

Each transition emits an event with context:
- TaskAssigned, TaskReassigned, TaskStarted, TaskCompleted, TaskCanceled, TaskPaused, TaskCreated, TaskUpdated

## 7. Business Rules
- Title must be unique per reporter while state in {NEW, ASSIGNED, IN_PROGRESS}.
- Cannot complete a task without an assignee.
- Cannot assign if already COMPLETED or CANCELED.
- Due date must be >= createdAt.

## 8. API Requirements
- POST /tasks
  - Create a task. Returns created entity and TaskCreated event.
- GET /tasks/{id}
  - Returns the task with current state.
- PATCH /tasks/{id}
  - Update mutable fields: title, description, priority, dueAt, tags.
- POST /tasks/{id}/assign
  - Body: { assigneeId }
  - Transition: assign -> ASSIGNED; emits TaskAssigned or TaskReassigned.
- POST /tasks/{id}/start
  - Transition: start -> IN_PROGRESS; emits TaskStarted.
- POST /tasks/{id}/complete
  - Preconditions: assigneeId not null.
  - Transition: complete -> COMPLETED; emits TaskCompleted.
- POST /tasks/{id}/pause
  - Transition: pause -> ASSIGNED; emits TaskPaused.
- POST /tasks/{id}/cancel
  - Transition: cancel -> CANCELED; emits TaskCanceled.

HTTP semantics:
- Use 201 for creations, 200 for successful transitions, 400 for validation issues, 404 if not found, 409 for invalid transitions.

## 9. Processors & Side-Effects
- NotificationProcessor
  - On TaskAssigned, TaskReassigned, TaskStarted, TaskCompleted, TaskCanceled
  - Sends user-friendly notifications to reporter and assignee.
- SLAProcessor
  - Periodically reviews IN_PROGRESS tasks and flags those past dueAt.
  - Emits TaskSlaBreached event and tags the task with "sla-breached".
- AuditProcessor
  - Listens to all Task* events and persists an audit trail.

## 10. Validation & Error Handling
- Return structured error objects: { code, message, details }.
- Reject transitions that violate business rules with 409 and include details.

## 11. Security & Access Control
- Auth required for all mutations.
- Reporter can update tasks they created.
- Assignee can change progress-related transitions.
- Admin can perform any action.

## 12. Observability
- Emit events with correlationId and actor metadata.
- Capture latency metrics per endpoint and processor.

## 13. Non-Functional Requirements
- API should handle at least 50 RPS with p95 < 200ms for reads and < 400ms for writes in baseline.
- Idempotency for transition endpoints via Idempotency-Key header.

## 14. Acceptance Criteria (high level)
- Can create a task and see it in NEW state.
- Can assign and start a task, progressing to IN_PROGRESS.
- Can complete a task and observe terminal COMPLETED state.
- Cannot perform invalid transitions (e.g., complete from NEW).
- Events generated for each transition are visible to processors.

## 15. Open Questions
- Should comments be a first-class entity or embedded in Task?
- Do we need bulk operations for assign/complete?

---
Next step: We will reflect these requirements in Canvas to finalize the design, then generate the application code. Update any section above and let me know when you're ready to build.