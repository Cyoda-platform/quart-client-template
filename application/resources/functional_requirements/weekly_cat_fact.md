# Weekly Cat Fact Subscription - Functional Requirements

## Overview
A lightweight Cyoda application that fetches a random cat fact once per week from the Cat Fact API (https://catfact.ninja) and emails it to all active subscribers. The system tracks send attempts and basic reporting metrics.

## User Stories
- As a visitor, I can subscribe with my email so I receive a weekly cat fact.
- As an admin, I can view subscriber counts and interaction metrics.
- As the system, fetch a single random cat fact each week and publish it to subscribers by email.

## Acceptance Criteria
- The system fetches a new fact from https://catfact.ninja once per scheduled run.
- Every active subscriber receives the fact via email within the scheduled window.
- Send attempts are recorded; failures are retried or logged.
- Dashboard shows subscriber count and send metrics (sent, failed, opens if tracked).

## Business Rules
- Emails are sent only to active subscribers who confirmed subscription.
- Respect API and email provider rate limits.
- Subscribers can unsubscribe; unsubscribed users won't receive future emails.

## Schedule
- Weekly at Monday 10:00 UTC by default (cron: 0 10 * * 1). Can be adjusted in Canvas.

## Reporting
- Subscriber count (total / active / weekly new)
- Send stats per run: total attempted, sent, failed
- Optional open/click tracking if email provider supports it

## Privacy & Compliance
- Store only necessary personal data (email, confirmation status).
- Provide an unsubscribe link in every email.
