# Weekly Cat Fact Subscription - Functional Requirements

## Overview

The Weekly Cat Fact Subscription app sends subscribers a unique cat fact every week. The app supports signup, confirmation, unsubscribe flows, scheduled ingestion of cat facts from the Cat Fact API, weekly email sends, interaction tracking, and admin reporting.

## Entities

- Subscriber
  - email (string)
  - name (string, optional)
  - status (enum: active, unsubscribed, pending)
  - subscribed_at (timestamp)
  - unsubscribed_at (timestamp, nullable)
  - verification_token (string, nullable)
  - consent_given_at (timestamp, nullable)

- CatFact
  - id (string/uuid)
  - text (string)
  - source (string)
  - retrieved_at (timestamp)

- SendEvent (Interaction)
  - subscriber_id (ref/email)
  - catfact_id (ref)
  - sent_at (timestamp)
  - delivered (boolean)
  - opened_at (timestamp, nullable)
  - clicked_at (timestamp, nullable)
  - failure_reason (string, nullable)

## Workflows

- weekly_ingest_workflow
  - Schedule: Weekly (configurable cadence)
  - Action: Call Cat Fact API (https://catfact.ninja/fact) to fetch a random fact
  - Deduplication: Check existing CatFact by text or id; if duplicate, skip
  - Store: Persist CatFact with retrieved_at
  - Error handling: Retry with exponential backoff up to 5 times

- weekly_send_workflow
  - Trigger: After ingest or scheduled shortly after ingest
  - Action: Read latest CatFact and fetch all Subscribers with status=active
  - For each subscriber: create SendEvent, generate email content, send via email provider
  - Retry: Retries for transient failures with backoff; log permanent failures
  - Tracking: Include tracking pixel and redirect links for click tracking

- interaction_tracking_workflow
  - Endpoints to capture open (pixel request) and click (redirect)
  - Update SendEvent with opened_at or clicked_at
  - Ensure privacy and validation of subscriber identifiers

## API Endpoints

- POST /signup
  - Creates Subscriber with status pending or active
  - Generates verification_token if confirmation required
  - Sends confirmation email if verification is on

- GET /confirm?token=...
  - Validates token and marks Subscriber active, sets subscribed_at

- GET /unsubscribe?email=...&token=...
  - Marks Subscriber unsubscribed and sets unsubscribed_at

- Admin endpoints (authenticated)
  - GET /admin/metrics/active_subscribers
  - GET /admin/metrics/weekly_sends
  - GET /admin/metrics/open_rate
  - GET /admin/metrics/click_rate
  - GET /admin/metrics/unsubscribe_rate

## Email Template

- HTML email with placeholders: {{name}}, {{cat_fact_text}}, {{unsubscribe_link}}, {{open_pixel}}
- Include unsubscribe link in every email
- Include tracking pixel for opens and redirect links for clicks

## Reporting & Metrics

- Active subscriber count
- Weekly sends total
- Open rate = opens / delivered
- Click rate = clicks / delivered
- Unsubscribe rate = unsubscribes / delivered

## Scheduling & Reliability

- Schedule ingestion weekly
- Implement deduplication for facts
- Rate limit calls to Cat Fact API and use safe retries

## Security & Compliance

- Respect unsubscribe requests immediately
- Store consent metadata
- Ensure verification tokens are single-use and expire

## Data Retention

- Retain SendEvent and CatFact records for at least 90 days
- Provide a data deletion path on user request

## TODOs

- Wire a real email provider integration (SMTP/SendGrid/SES) and credential storage
- Implement admin authentication and dashboard UI
- Add end-to-end tests and monitoring
