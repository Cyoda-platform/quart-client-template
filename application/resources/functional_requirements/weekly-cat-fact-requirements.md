# Weekly Cat Fact Subscription - Functional Requirements

Overview

We will build a lightweight Python application that retrieves a weekly cat fact from the Cat Fact API (https://catfact.ninja/#/Facts/getRandomFact) and sends it via email to subscribers. The app will be scheduled to run once per week and will include subscriber signup, email sending, and basic reporting.

Functional Requirements

1. Data Ingestion
   - Schedule a weekly job to call the Cat Fact API and retrieve a single random fact.
   - Persist retrieved facts in a facts store with timestamp and source metadata.

2. Subscriber Management
   - Public signup endpoint for users to subscribe with email and optional name.
   - Unsubscribe link included in every email.
   - Simple confirmation flow (double opt-in) is optional but recommended.

3. Publishing (Email Delivery)
   - Use Cyoda-managed email delivery to send the weekly cat fact to all confirmed subscribers.
   - Emails include the fact text, fact metadata (length, source), and an unsubscribe link.
   - Retry logic for transient delivery failures.

4. Scheduling
   - The ingestion + send job runs once per week. Schedule configurable via environment variable.

5. Reporting
   - Track total subscriber count, weekly emails sent, delivery successes/failures, open/click metrics if available from Cyoda-managed email.
   - Expose a simple reporting endpoint or admin view that summarizes the last 30 days.

6. Observability
   - Log ingestion attempts, API responses, send attempts, and errors.
   - Basic health endpoint.

7. Security & Privacy
   - Store subscriber emails securely (encrypted at rest if possible).
   - Provide unsubscribe and data deletion options to comply with privacy regulations.

Non-functional Requirements

- Language: Python (Quart framework from Cyoda template)
- Lightweight and cost-effective; low throughput expected
- Configurable scheduling and email templates via environment variables

Deliverables

- Functional requirements document (this file)
- Entity definitions for Subscriber and CatFact
- Workflow definitions: WeeklyIngestionAndEmailSend
- Skeleton application with endpoints for sign-up, unsubscribe, reporting, and scheduled job

