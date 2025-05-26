```python
import asyncio
import datetime
import logging
from typing import Dict, List

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# In-memory storage mocks
subscribers: List[str] = []
games_storage: Dict[str, List[Dict]] = {}
entity_jobs: Dict[str, Dict] = {}

API_KEY = "test"
EXTERNAL_API_URL = "https://api.sportsdata.io/v3/nba/scores/json/ScoresBasicFinal/{date}?key={key}"

# Utility: Validate date string format YYYY-MM-DD
def validate_date(date_str: str) -> bool:
    try:
        datetime.datetime.strptime(date_str, "%Y-%m-%d")
        return True
    except Exception:
        return False

# Async fetch external NBA scores
async def fetch_nba_scores(date: str) -> List[Dict]:
    url = EXTERNAL_API_URL.format(date=date, key=API_KEY)
    async with httpx.AsyncClient() as client:
        r = await client.get(url)
        r.raise_for_status()
        data = r.json()
        # TODO: Confirm exact shape of the external API data and adapt if needed
        return data if isinstance(data, list) else []

# Async send emails mock (fire and forget)
async def send_email_batch(emails: List[str], date: str, games: List[Dict]):
    # TODO: Replace with real email sending service integration
    summary_lines = []
    for game in games:
        summary_lines.append(
            f"{game.get('HomeTeam','?')} {game.get('HomeTeamScore','?')} - "
            f"{game.get('AwayTeam','?')} {game.get('AwayTeamScore','?')}"
        )
    summary = "\n".join(summary_lines) or "No games found for this date."
    for email in emails:
        logger.info(f"Sending email to {email} for {date}:\n{summary}")
    # Simulate async email sending delay
    await asyncio.sleep(0.1)

# Background task to fetch/store scores and notify subscribers
async def process_scores_and_notify(date: str):
    job_id = f"job_{date}"
    entity_jobs[job_id] = {"status": "processing", "requestedAt": datetime.datetime.utcnow().isoformat()}
    try:
        games = await fetch_nba_scores(date)
        # Store games locally keyed by date
        games_storage[date] = []
        for g in games:
            # Normalize/Extract relevant info for storage
            games_storage[date].append({
                "date": date,
                "home_team": g.get("HomeTeam"),
                "away_team": g.get("AwayTeam"),
                "home_score": g.get("HomeTeamScore"),
                "away_score": g.get("AwayTeamScore"),
                # TODO: Add other relevant fields as needed
            })
        logger.info(f"Fetched and stored {len(games)} games for {date}")
        # Notify subscribers
        if subscribers:
            await send_email_batch(subscribers, date, games_storage[date])
            logger.info(f"Sent notifications to {len(subscribers)} subscribers for {date}")
        else:
            logger.info("No subscribers to notify.")
        entity_jobs[job_id]["status"] = "completed"
    except Exception as e:
        logger.exception(e)
        entity_jobs[job_id]["status"] = "failed"

@app.route("/subscribe", methods=["POST"])
async def subscribe():
    data = await request.get_json(force=True)
    email = data.get("email")
    if not email or not isinstance(email, str):
        return jsonify({"error": "Invalid or missing email"}), 400
    if email in subscribers:
        return jsonify({"error": "Email already subscribed"}), 400
    subscribers.append(email)
    logger.info(f"New subscription: {email}")
    return jsonify({"message": f"Subscribed {email} successfully"}), 201

@app.route("/fetch-scores", methods=["POST"])
async def fetch_scores():
    data = await request.get_json(force=True)
    date = data.get("date")
    if not date or not validate_date(date):
        return jsonify({"error": "Invalid or missing date (expected YYYY-MM-DD)"}), 400

    # Fire and forget processing
    asyncio.create_task(process_scores_and_notify(date))

    return jsonify({"message": f"Fetching and processing scores for {date} started"}), 200

@app.route("/notify", methods=["POST"])
async def notify():
    data = await request.get_json(force=True)
    date = data.get("date")
    if not date or not validate_date(date):
        return jsonify({"error": "Invalid or missing date (expected YYYY-MM-DD)"}), 400
    games = games_storage.get(date)
    if not games:
        return jsonify({"error": "No game data found for the specified date"}), 404
    if not subscribers:
        return jsonify({"message": "No subscribers to notify"}), 200

    try:
        await send_email_batch(subscribers, date, games)
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to send notifications"}), 500

    return jsonify({"message": f"Notifications sent to {len(subscribers)} subscribers for {date}"}), 200

@app.route("/subscribers", methods=["GET"])
async def get_subscribers():
    return jsonify({"subscribers": subscribers})

@app.route("/games/all", methods=["GET"])
async def get_all_games():
    # Optional pagination (not implemented in prototype)
    all_games = []
    for date_games in games_storage.values():
        all_games.extend(date_games)
    return jsonify({"games": all_games})

@app.route("/games/<date>", methods=["GET"])
async def get_games_by_date(date):
    if not validate_date(date):
        return jsonify({"error": "Invalid date format (expected YYYY-MM-DD)"}), 400
    games = games_storage.get(date)
    if not games:
        return jsonify({"date": date, "games": []})
    return jsonify({"date": date, "games": games})

# Scheduler stub
async def daily_scheduler():
    while True:
        now = datetime.datetime.utcnow()
        target_time = now.replace(hour=18, minute=0, second=0, microsecond=0)
        if now > target_time:
            target_time += datetime.timedelta(days=1)
        wait_seconds = (target_time - now).total_seconds()
        logger.info(f"Scheduler sleeping for {wait_seconds} seconds until next fetch/notify cycle.")
        await asyncio.sleep(wait_seconds)

        today_str = target_time.strftime("%Y-%m-%d")
        logger.info(f"Scheduler triggered for date: {today_str}")
        await process_scores_and_notify(today_str)

if __name__ == '__main__':
    # Start scheduler task
    loop = asyncio.get_event_loop()
    loop.create_task(daily_scheduler())

    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
```
