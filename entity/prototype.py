```python
import asyncio
import logging
from datetime import datetime
from typing import Dict, List

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# In-memory mock persistence
subscribers: set = set()
games_data: Dict[str, List[dict]] = {}  # key = date str YYYY-MM-DD, value = list of game dicts

# Mock entity job tracker for async fetch tasks
entity_job: Dict[str, dict] = {}

NBA_API_KEY = "test"  # from requirements; real key should replace this
NBA_API_URL = "https://api.sportsdata.io/v3/nba/scores/json/ScoresBasicFinal/{date}?key=" + NBA_API_KEY

# TODO: Replace with real email sending logic
async def send_email(to_email: str, subject: str, body: str):
    logger.info(f"Sending email to {to_email} with subject '{subject}'")
    # Simulate sending
    await asyncio.sleep(0.1)
    # TODO: Implement real email sending
    logger.info(f"Email sent to {to_email}")

async def fetch_and_store_scores(date: str):
    logger.info(f"Started fetching scores for {date}")
    async with httpx.AsyncClient() as client:
        try:
            url = NBA_API_URL.format(date=date)
            response = await client.get(url, timeout=10)
            response.raise_for_status()
            scores = response.json()
            # Basic validation, expect list
            if not isinstance(scores, list):
                logger.error(f"Unexpected API response format for date {date}: {scores}")
                return False

            # Store (replace existing)
            games_data[date] = scores
            logger.info(f"Stored {len(scores)} games for {date}")

            # Notify subscribers
            if subscribers:
                summary = build_summary_email(date, scores)
                send_tasks = [send_email(email, f"NBA Scores for {date}", summary) for email in subscribers]
                await asyncio.gather(*send_tasks)
                logger.info(f"Notifications sent to {len(subscribers)} subscribers")
            else:
                logger.info("No subscribers to notify")

            return True
        except Exception as e:
            logger.exception(f"Failed fetching or storing scores for {date}: {e}")
            return False

def build_summary_email(date: str, scores: List[dict]) -> str:
    lines = [f"NBA Scores for {date}:\n"]
    for game in scores:
        home = game.get("HomeTeam", "N/A")
        away = game.get("AwayTeam", "N/A")
        home_score = game.get("HomeTeamScore", "N/A")
        away_score = game.get("AwayTeamScore", "N/A")
        lines.append(f"{away} @ {home} : {away_score} - {home_score}")
    return "\n".join(lines)

@app.route("/subscribe", methods=["POST"])
async def subscribe():
    data = await request.get_json(force=True)
    email = data.get("email")
    if not email or not isinstance(email, str):
        return jsonify({"status": "error", "message": "Invalid or missing email"}), 400
    if email in subscribers:
        return jsonify({"status": "success", "message": "Email already subscribed"})
    subscribers.add(email)
    logger.info(f"New subscriber added: {email}")
    return jsonify({"status": "success", "message": "Subscription successful."})

@app.route("/subscribers", methods=["GET"])
async def get_subscribers():
    return jsonify({"subscribers": list(subscribers)})

@app.route("/games/all", methods=["GET"])
async def get_all_games():
    # Pagination parameters
    try:
        page = int(request.args.get("page", 1))
        page_size = int(request.args.get("page_size", 20))
    except ValueError:
        return jsonify({"status": "error", "message": "Invalid pagination parameters"}), 400

    all_games = []
    for games_list in games_data.values():
        all_games.extend(games_list)

    total_items = len(all_games)
    total_pages = (total_items + page_size - 1) // page_size
    if page < 1 or page > total_pages and total_pages > 0:
        return jsonify({"status": "error", "message": "Page out of range"}), 400

    start = (page - 1) * page_size
    end = start + page_size
    paged_games = all_games[start:end]

    return jsonify({
        "games": paged_games,
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
            "total_items": total_items
        }
    })

@app.route("/games/<date>", methods=["GET"])
async def get_games_by_date(date: str):
    # Validate date format YYYY-MM-DD (basic)
    try:
        datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        return jsonify({"status": "error", "message": "Invalid date format, expected YYYY-MM-DD"}), 400

    games = games_data.get(date)
    if games is None:
        return jsonify({"status": "error", "message": "No data for given date"}), 404
    return jsonify({
        "date": date,
        "games": games
    })

@app.route("/fetch-scores", methods=["POST"])
async def fetch_scores():
    data = await request.get_json(force=True)
    date = data.get("date")
    if not date or not isinstance(date, str):
        return jsonify({"status": "error", "message": "Missing or invalid date"}), 400
    try:
        datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        return jsonify({"status": "error", "message": "Invalid date format, expected YYYY-MM-DD"}), 400

    job_id = f"fetch_{date}"
    if job_id in entity_job and entity_job[job_id]["status"] == "processing":
        return jsonify({"status": "error", "message": "Fetch job already in progress for this date"}), 409

    entity_job[job_id] = {"status": "processing", "requestedAt": datetime.utcnow().isoformat()}
    # Fire and forget the processing task
    asyncio.create_task(_process_fetch_job(job_id, date))

    return jsonify({"status": "success", "message": "Fetch job started"})

async def _process_fetch_job(job_id: str, date: str):
    success = await fetch_and_store_scores(date)
    entity_job[job_id]["status"] = "done" if success else "failed"
    entity_job[job_id]["finishedAt"] = datetime.utcnow().isoformat()
    logger.info(f"Fetch job {job_id} finished with status {entity_job[job_id]['status']}")

# TODO: Implement scheduler to trigger fetch_and_store_scores(date) daily at 18:00 UTC
# This can be done with APScheduler or asyncio loops in production.

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
```
