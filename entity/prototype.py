```python
import asyncio
import logging
from datetime import datetime, date
from typing import Optional

import httpx
from quart import Quart, request, jsonify
from quart_schema import QuartSchema

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# In-memory cache for prototype persistence
# Structure:
# reports: { "YYYY-MM-DD": {... report data ...} }
# user_summaries: { userId: {... user summary ...} }
# ingestion_jobs: { job_id: {status, requestedAt} }
reports = {}
user_summaries = {}
ingestion_jobs = {}

FAKEREST_API_ACTIVITIES_URL = "https://fakerestapi.azurewebsites.net/api/v1/Activities"

# Helper: fetch activities from Fakerest API for given date (simulate filtering by date)
async def fetch_activities_for_date(target_date: date):
    async with httpx.AsyncClient() as client:
        try:
            # Fetch all activities from Fakerest API
            resp = await client.get(FAKEREST_API_ACTIVITIES_URL)
            resp.raise_for_status()
            activities = resp.json()
        except Exception as e:
            logger.exception(f"Failed to fetch activities from Fakerest API: {e}")
            raise

    # TODO: Fakerest API does not have date filtering on activities;
    # so we simulate filtering by created date or similar - here we just return all.
    # In real implementation, add date filtering logic if API supports it.
    return activities


# Helper: analyze activities to extract patterns and anomalies
def analyze_activities(activities):
    # Example analysis: count activity types frequency and identify anomalies
    activity_frequency = {}
    user_activity_count = {}

    for act in activities:
        user_id = act.get("idUser")
        activity_type = act.get("activity", "unknown")  # Fakerest API returns 'activity' field?

        # TODO: Fakerest API's Activities schema has: id, title, dueDate, completed
        # It lacks userId and activity type fields, so we'll improvise:
        # Use 'title' as activity type and 'id' as userId (mock)
        user_id = act.get("id", 0)  # Using id as a proxy for userId (mock)
        activity_type = act.get("title", "unknown")

        user_activity_count[user_id] = user_activity_count.get(user_id, 0) + 1
        activity_frequency[activity_type] = activity_frequency.get(activity_type, 0) + 1

    # Define anomalies as users with activity count greater than mean + stddev (simple)
    counts = list(user_activity_count.values())
    if counts:
        mean_count = sum(counts) / len(counts)
        variance = sum((x - mean_count) ** 2 for x in counts) / len(counts)
        stddev = variance ** 0.5
        threshold = mean_count + stddev
    else:
        threshold = 0

    anomalies = []
    for uid, cnt in user_activity_count.items():
        if cnt > threshold:
            anomalies.append({
                "userId": uid,
                "description": "Unusually high activity frequency"
            })

    return {
        "totalUsers": len(user_activity_count),
        "totalActivities": len(activities),
        "activityFrequency": activity_frequency,
        "anomalies": anomalies,
    }


# Background processing task for ingestion
async def process_ingestion(job_id: str, target_date: date):
    try:
        logger.info(f"Processing ingestion job {job_id} for date {target_date}")
        activities = await fetch_activities_for_date(target_date)
        analysis = analyze_activities(activities)

        # Save report in cache
        reports[target_date.isoformat()] = analysis

        # Save per-user summaries (mock simple)
        user_summaries.clear()
        for act in activities:
            user_id = act.get("id", 0)
            activity_type = act.get("title", "unknown")
            summary = user_summaries.get(user_id, {"totalActivities": 0, "activityTypes": {}})
            summary["totalActivities"] += 1
            summary["activityTypes"][activity_type] = summary["activityTypes"].get(activity_type, 0) + 1
            user_summaries[user_id] = summary

        ingestion_jobs[job_id]["status"] = "completed"
        logger.info(f"Ingestion job {job_id} completed")
    except Exception as e:
        ingestion_jobs[job_id]["status"] = "failed"
        logger.exception(f"Ingestion job {job_id} failed: {e}")


@app.route("/api/activities/ingest", methods=["POST"])
async def ingest_activities():
    data = await request.get_json(force=True)
    date_str = data.get("date")
    try:
        target_date = datetime.strptime(date_str, "%Y-%m-%d").date() if date_str else date.today()
    except Exception:
        return jsonify({"status": "error", "message": "Invalid date format, expected YYYY-MM-DD"}), 400

    job_id = f"job-{datetime.utcnow().isoformat()}"
    ingestion_jobs[job_id] = {"status": "processing", "requestedAt": datetime.utcnow().isoformat()}

    # Fire and forget ingestion processing
    asyncio.create_task(process_ingestion(job_id, target_date))

    return jsonify({
        "status": "success",
        "message": f"Data ingestion and processing started for date {target_date.isoformat()}",
        "jobId": job_id
    })


@app.route("/api/activities/report", methods=["GET"])
async def get_report():
    date_str = request.args.get("date")
    if not date_str:
        return jsonify({"status": "error", "message": "Missing required query parameter: date"}), 400

    report = reports.get(date_str)
    if not report:
        return jsonify({"status": "error", "message": f"No report found for date {date_str}"}), 404

    response = {"date": date_str}
    response.update(report)
    return jsonify(response)


@app.route("/api/activities/users/<int:user_id>", methods=["GET"])
async def get_user_summary(user_id: int):
    summary = user_summaries.get(user_id)
    if not summary:
        return jsonify({"status": "error", "message": f"No activity summary found for user {user_id}"}), 404

    # For prototype, dateRange is static placeholder
    response = {
        "userId": user_id,
        "activitySummary": {
            "dateRange": "N/A - N/A",  # TODO: track date range of activities per user if needed
            "totalActivities": summary["totalActivities"],
            "activityTypes": summary["activityTypes"],
        }
    }
    return jsonify(response)


@app.route("/api/activities/send-report", methods=["POST"])
async def send_report():
    data = await request.get_json(force=True)
    date_str = data.get("date")
    admin_email = data.get("adminEmail")

    if not date_str or not admin_email:
        return jsonify({"status": "error", "message": "Missing required fields: date and adminEmail"}), 400

    report = reports.get(date_str)
    if not report:
        return jsonify({"status": "error", "message": f"No report found for date {date_str}"}), 404

    # TODO: Implement real email sending logic using an email service provider
    # For prototype, simulate sending email with a log message
    logger.info(f"Simulating sending report for {date_str} to admin email: {admin_email}")

    return jsonify({
        "status": "success",
        "message": f"Report sent to {admin_email} for date {date_str}"
    })


if __name__ == '__main__':
    import sys
    import logging

    # Setup basic logging to stdout
    logging.basicConfig(stream=sys.stdout, level=logging.INFO,
                        format='%(asctime)s %(levelname)s %(name)s: %(message)s')

    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
```
