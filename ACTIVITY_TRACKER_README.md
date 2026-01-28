# Activity Tracker Application

A Cyoda-based application that ingests user activity data from the Fakerest API, analyzes patterns, detects anomalies, and publishes daily summary reports via email.

## Overview

The Activity Tracker follows the **Interface-based** and **Workflow-driven** architecture pattern defined in the Cyoda framework. It implements a complete pipeline for:

1. **Data Ingestion** - Fetches activity data from Fakerest API with retry logic
2. **Data Processing** - Aggregates data, detects anomalies using z-score method
3. **Report Generation** - Creates HTML and plaintext reports
4. **Email Publishing** - Sends reports to configured admin email

## Architecture

### Entity: ActivityReport

Located in `application/entity/activity_report/version_1/activity_report.py`

**Key Fields:**
- `report_date` - Date of the report (YYYY-MM-DD)
- `total_activities` - Total number of activities for the day
- `top_activity_types` - Top 5 activity types with counts
- `trend_highlights` - Trend analysis vs 7-day average
- `flagged_anomalies` - Users/activity types with z-score > 3
- `report_content_html` - HTML formatted report
- `report_content_text` - Plaintext formatted report
- `email_sent_at` - Timestamp when report was emailed
- `email_recipient` - Email address where report was sent

### Workflow States

```
initial_state → ingested → processed → reported → completed
```

**Transitions:**
- `ingest` - Fetches data from Fakerest API (ActivityReportIngestionProcessor)
- `process` - Aggregates data and detects anomalies (ActivityReportProcessingProcessor)
- `report` - Generates and sends email report (ActivityReportPublishingProcessor)
- `complete` - Marks report as completed

## Processors

### ActivityReportIngestionProcessor

Fetches activity data from the Fakerest API with exponential backoff retry logic.

**Features:**
- Handles rate limiting (HTTP 429)
- Retries transient errors up to 3 times
- Exponential backoff: 1s, 2s, 4s
- Timeout handling (30s per request)
- Stores raw data location for traceability

### ActivityReportProcessingProcessor

Aggregates daily data and detects anomalies.

**Features:**
- Calculates top 5 activity types
- Generates trend highlights (% change vs 7-day average)
- Detects anomalies using z-score method (threshold: 3.0)
- Analyzes both user activity counts and activity type frequencies

### ActivityReportPublishingProcessor

Generates formatted reports and sends via email.

**Features:**
- Generates HTML formatted report with styling
- Generates plaintext fallback for email clients
- Sends via SMTP with optional authentication
- Supports TLS/STARTTLS

## API Endpoints

All endpoints are prefixed with `/api/activity-reports`

### CRUD Operations

- `POST /` - Create new ActivityReport
- `GET /<entity_id>` - Get ActivityReport by ID
- `GET /` - List all ActivityReports
- `PUT /<entity_id>` - Update ActivityReport
- `DELETE /<entity_id>` - Delete ActivityReport

### Workflow Operations

- `GET /<entity_id>/transitions` - Get available transitions
- `POST /<entity_id>/transition/<transition_name>` - Trigger transition

## Scheduled Job

The application includes a daily scheduler that runs at a configurable time (default: 02:00 UTC).

**Location:** `application/scheduler.py`

**Usage:**
```python
from application.scheduler import start_scheduler
import asyncio

asyncio.run(start_scheduler())
```

## Configuration

### Environment Variables

**Scheduling:**
- `SCHEDULE_TIME` - Time to run daily pipeline (HH:MM format, default: "02:00")

**Email Configuration:**
- `ADMIN_EMAIL` - Email address for reports (default: "admin@example.com")
- `SMTP_HOST` - SMTP server hostname (default: "localhost")
- `SMTP_PORT` - SMTP server port (default: "587")
- `SMTP_USER` - SMTP username (optional)
- `SMTP_PASSWORD` - SMTP password (optional)
- `SENDER_EMAIL` - Sender email address (default: "noreply@activity-tracker.local")

**Cyoda Configuration:**
- `CYODA_CLIENT_ID` - Cyoda platform client ID
- `CYODA_CLIENT_SECRET` - Cyoda platform client secret
- `CYODA_TOKEN_URL` - Cyoda platform token URL
- `CHAT_REPOSITORY` - Repository type ("cyoda" or other for in-memory)

## Running Locally

### Prerequisites

- Python 3.9+
- Virtual environment activated
- Dependencies installed: `pip install -r requirements.txt`

### Start the Application

```bash
# Set environment variables
export ADMIN_EMAIL="your-email@example.com"
export SMTP_HOST="smtp.gmail.com"
export SMTP_PORT="587"
export SMTP_USER="your-email@gmail.com"
export SMTP_PASSWORD="your-app-password"

# Run the application
python -m quart --app application.app:app run
```

### Run the Scheduler

```bash
# In a separate terminal
python -c "
import asyncio
from application.scheduler import start_scheduler
asyncio.run(start_scheduler())
"
```

### Run Tests

```bash
# Run all tests
pytest tests/

# Run Activity Tracker tests only
pytest tests/unit/test_activity_report_processors.py -v

# Run with coverage
pytest tests/ --cov=application --cov-report=html
```

## Testing

The application includes comprehensive unit tests for:

- **Ingestion Processor** - API fetching, retry logic, error handling
- **Processing Processor** - Data aggregation, anomaly detection, trend analysis
- **Publishing Processor** - Report generation, email formatting

**Test File:** `tests/unit/test_activity_report_processors.py`

**Key Test Cases:**
- Processor initialization
- Entity transformation
- Top activity type generation
- Anomaly detection with z-scores
- Trend highlight generation
- Edge cases (zero activities, large counts)

## Code Quality

The application follows Cyoda development guidelines:

```bash
# Format code
python -m black . && python -m isort .

# Type checking
python -m mypy .

# Linting
python -m flake8 .

# Security scanning
python -m bandit -r . -x tests/
```

## Data Flow

```
1. Scheduler triggers at 02:00 UTC
   ↓
2. Create ActivityReport entity
   ↓
3. Trigger "ingest" transition
   → ActivityReportIngestionProcessor fetches from Fakerest API
   ↓
4. Trigger "process" transition
   → ActivityReportProcessingProcessor aggregates and detects anomalies
   ↓
5. Trigger "report" transition
   → ActivityReportPublishingProcessor generates and sends email
   ↓
6. Trigger "complete" transition
   → Report marked as completed
```

## Anomaly Detection

The application uses the z-score method to detect anomalies:

```
z-score = (value - mean) / standard_deviation
```

**Threshold:** z-score > 3.0 (approximately 99.7% confidence)

**Analyzed Metrics:**
- User activity counts (identifies users with unusual activity)
- Activity type frequencies (identifies unusual activity patterns)

## Example Report

### HTML Format
```html
<h1>Daily Activity Report</h1>
<p><strong>Report Date:</strong> 2026-01-28</p>
<p><strong>Total Activities:</strong> 1250</p>

<h3>Top Activity Types</h3>
<ol>
  <li>login: 450 activities</li>
  <li>view_page: 380 activities</li>
  ...
</ol>

<h3>Trend Highlights</h3>
<ul>
  <li>+15% increase vs 7-day average</li>
  <li>Peak activity at 14:30 UTC</li>
</ul>

<h3>Flagged Anomalies</h3>
<ul>
  <li>user: user_42 (z-score: 3.5) - Unusual spike in activity count</li>
</ul>
```

### Plaintext Format
```
============================================================
DAILY ACTIVITY REPORT
============================================================
Report Date: 2026-01-28
Total Activities: 1250

TOP ACTIVITY TYPES:
  - login: 450 activities
  - view_page: 380 activities
  ...

TREND HIGHLIGHTS:
  - +15% increase vs 7-day average
  - Peak activity at 14:30 UTC

FLAGGED ANOMALIES:
  - user: user_42 (z-score: 3.5) - Unusual spike in activity count
```

## Troubleshooting

### API Connection Issues

If the Fakerest API is unreachable:
- Check network connectivity
- Verify API endpoint: https://fakerestapi.azurewebsites.net
- Check logs for retry attempts and backoff timing

### Email Not Sending

- Verify SMTP configuration
- Check SMTP credentials
- Ensure firewall allows SMTP port (usually 587)
- Check email logs for authentication errors

### Anomaly Detection Not Working

- Ensure sufficient data (at least 2 data points for z-score calculation)
- Check that z-score threshold is set correctly (default: 3.0)
- Review processing logs for calculation errors

## Future Enhancements

- [ ] Support for multiple email recipients
- [ ] Configurable anomaly detection thresholds
- [ ] Historical trend analysis (30-day, 90-day)
- [ ] Custom report templates
- [ ] Slack/Teams integration for notifications
- [ ] Database persistence for historical data
- [ ] Advanced statistical methods (IQR, isolation forest)
- [ ] Real-time activity streaming

## License

See LICENSE file in repository root.

