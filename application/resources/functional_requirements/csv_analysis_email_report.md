# CSV Analysis and Email Report Application

## Overview
This application downloads a CSV file, analyzes it with pandas, and sends analysis reports to email subscribers.

## Entities

### DataAnalysis
Represents a CSV analysis job that downloads, processes, and analyzes data.

**States:**
- `initial_state` → `created` (automatic)
- `created` → `validated` (automatic, via validation criterion)
- `validated` → `analyzed` (automatic, via processor)
- `analyzed` → `completed` (automatic)

**Fields:**
- `csv_url`: URL to the CSV file (required)
- `file_name`: Name of the downloaded file
- `row_count`: Number of rows in the CSV
- `column_count`: Number of columns
- `columns`: List of column names
- `summary_stats`: Dictionary with summary statistics (mean, median, std, etc.)
- `analysis_result`: Full analysis result as JSON
- `status`: Current processing status
- `created_at`: Timestamp when created
- `updated_at`: Timestamp when last updated

### Subscriber
Represents an email subscriber who receives analysis reports.

**States:**
- `initial_state` → `created` (automatic)
- `created` → `active` (automatic)
- `active` → `inactive` (manual)
- `inactive` → `active` (manual)

**Fields:**
- `email`: Email address (required, unique)
- `name`: Subscriber name
- `is_active`: Whether subscriber receives reports
- `subscribed_at`: Timestamp when subscribed
- `last_report_sent`: Timestamp of last report sent
- `report_count`: Number of reports received

## Workflow

1. **Create DataAnalysis**: User submits CSV URL
2. **Validate**: Check URL format and accessibility
3. **Analyze**: Download CSV, analyze with pandas, compute statistics
4. **Complete**: Mark as completed
5. **Send Reports**: For each active Subscriber, send analysis report via email

## Technical Requirements

- Download CSV from URL using requests/urllib
- Parse and analyze with pandas
- Compute: row count, column count, summary statistics
- Send emails to subscribers (mock implementation)
- Handle errors gracefully

