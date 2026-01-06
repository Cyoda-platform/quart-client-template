# Weekly Books Analytics - Functional Requirements

Objective
---------
Build an automated weekly analytics application that:

- Extracts book data from the Fake REST API: https://fakerestapi.azurewebsites.net
- Collects the following fields for each book: id, title, description, pageCount, excerpt, publishDate
- Analyzes the data to produce insights including:
  - Total page counts across all books
  - Top titles by pageCount (top 10)
  - Distribution of publication dates (by year)
  - Brief descriptions and excerpts for the most popular titles
- Generates a summary report with the above insights and emails it to the analytics team on a weekly schedule (every Wednesday)

Data Extraction
---------------
- Source: https://fakerestapi.azurewebsites.net/api/Books
- Fields to collect: id, title, description, pageCount, excerpt, publishDate
- Incremental fetch: not required for initial MVP; full fetch on each run is acceptable

Analysis Metrics
----------------
- Total pages: sum(pageCount) across all books
- Top titles: sort by pageCount descending and select top 10
- Publication distribution: group by publish year and count books per year
- Popular titles details: include title, pageCount, brief description (truncate to 300 chars), and excerpt

Scheduling & Delivery
---------------------
- Schedule: every Wednesday at 09:00 UTC (cron: 0 9 * * 3)
- Delivery: Email to analytics-team@example.com (configurable)
- Email format: plain text with an attached CSV of the top titles and a simple summary in the email body

Operational
-----------
- The repository will contain code, workflow definitions, and scheduling configuration
- Logs and error notifications should be sent to the development team via console and email

Security & Configuration
------------------------
- No authentication required for the Fake REST API
- Email delivery will use environment-configured SMTP credentials; do not store credentials in repo

MVP Scope
---------
- Full weekly fetch, analysis, and email delivery
- Unit tests for data extraction and analysis routines

Notes
-----
- The repository follows GitOps practices; this requirements file is saved to the branch as the single source of truth.
