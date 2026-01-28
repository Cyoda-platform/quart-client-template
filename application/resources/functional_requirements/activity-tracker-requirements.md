# Activity Tracker - Functional Requirements

## Overview
Activity Tracker ingests user activity data from the Fakerest API (https://fakerestapi.azurewebsites.net), analyzes user activity patterns, and publishes daily summary reports to an admin email.

## Schedule
- The ingestion and processing pipeline must run once per day (scheduled job).

## Data Ingestion
- Fetch activity data for all users from the Fakerest API.
- Handle API rate limits and transient errors with retries and exponential backoff.
- Persist raw fetched data to a daily partitioned store for traceability.

## Data Processing & Analysis
- Aggregate daily totals per user and overall totals.
- Identify top activity types across the user base for the day.
- Detect anomalies using a statistical z-score method applied to activity counts and activity-type frequencies. Flag any users or activity types with z-score > 3.

## Reporting
- Generate a compact daily report including:
  - Total activities today
  - Top 5 activity types with counts
  - Brief trend highlights (e.g., +/−% change vs. 7-day average)
  - List of flagged anomalies (user IDs or activity types with z-score > 3)
- Reports must be formatted for an admin email (HTML + plaintext fallback).

## Publishing
- Email the daily report to a configurable admin email.
- Support SMTP configuration via environment variables.

## Non-functional
- Use a GitOps workflow; repository is the single source of truth.
- Schedule must be configurable (cron-style) and default to daily at 02:00 UTC.
- Ensure logs and basic metrics are emitted for monitoring.

## Deliverables
- Ingestion job, processing pipeline, reporting generation, and email publishing.
- Tests for ingestion and processing logic.
- README with setup and how to run locally.
