# Weekly Cat Fact Subscription - Functional Requirements

## Overview
A Python-based service that retrieves a cat fact weekly from the Cat Fact API and emails it to subscribers. Uses customer-provided SMTP for email delivery and provides standard reporting (subscriber count, weekly send status, opens/clicks).

## Functional Requirements

1. Data Ingestion
   - A scheduled job runs once per week to retrieve a random cat fact from https://catfact.ninja/#/Facts/getRandomFact.
   - The job stores the fetched cat fact in the CatFact entity and marks it with a send_date.

2. Subscription Management
   - Users can subscribe with email address and optional name.
   - Subscribers can unsubscribe via a unique link in the email.
   - The system validates email format and prevents duplicate subscriptions.

3. Email Publishing
   - Every week, the system sends the latest CatFact to all active subscribers using the customer's SMTP server.
   - Emails include a unique unsubscribe link and basic tracking pixels for opens.
   - Include headers/tags to assist in email provider analytics.

4. Reporting
   - Track total subscribers, active subscribers, and unsubscribe events.
   - Track weekly send status (success/failure per send job).
   - Track open rates and click-throughs via tracking pixel and tracked links.

5. Operational
   - Configurable schedule (default: weekly), SMTP credentials provided via environment variables managed by the Environment Agent.
   - Logging and basic error reporting for ingestion and email publishing jobs.

6. Security & Privacy
   - Store subscriber emails encrypted at rest.
   - Provide a privacy policy link in emails.

## Non-functional Requirements
- Scalable to 100k subscribers with batched sends.
- Retry logic on send failures with exponential backoff.
- Maintain audit logs for sends and unsubscribes.


## Deployment Notes
- SMTP credentials to be supplied through the Environment Agent.
- Use application configuration to set schedule and batching.
