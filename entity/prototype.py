```python
import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# --- Mocked in-memory persistence ---
# Structure:
# subscribers: set of emails
# games: dict keyed by date (YYYY-MM-DD) -> List of games dict
subscribers_cache: set = set()
games_cache: Dict[str, List[Dict]] = dict()

# External API info (real API endpoint, key is placeholder)
API_KEY = "test"
API_URL_TEMPLATE = "https://api.sportsdata.io/v3/nba/scores/json/ScoresBasicFinal/{date}?key=" + API_KEY

# Email sending mock function
async def send_email(to_emails: List[str], subject: str, body: str):
    # TODO: Implement real email sending using SMTP or external provider
    logger.info(f"Sending email to {to_emails} with subject {subject}")
    # Simulate async delay
    await asyncio.sleep(0.1)

# Helper: format email body with detailed scores
def format_scores_email(date: str, games: List[Dict]) -> str:
    if not games:
        return f"No NBA games found for {date}."
    lines = [f"NBA Scores for {date}:\n"]
    for game in games:
        line = (
            f"{game.get('away_team')} {game.get('away_score')} @ "
            f"{game.get('home_team')} {game.get('home_score')} (Status: {game.get('status')})"
        )
        lines.append(line)
    return "\n".join(lines)

# --- Business Logic: Fetch, store and notify ---
async def fetch_and_store_scores(date: str) -> Dict:
    url = API_URL_TEMPLATE.format(date=date)
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()
        except Exception as e:
            logger.exception(f"Failed to fetch NBA scores for {date}: {e}")
            raise

    # Parse and store relevant game data
    # According to example, keep: date, home_team, away_team, home_score, away_score, status
    stored_games = []
    for game in data:
        try:
            stored_games.append({
                "date": date,
                "home_team": game.get("HomeTeam"),
                "away_team": game.get("AwayTeam"),
                "home_score": game.get("HomeTeamScore"),
                "away_score": game.get("AwayTeamScore"),
                "status": game.get("Status")
            })
        except Exception as e:
            logger.warning(f"Skipping invalid game data: {game} ({e})")

    # Store in cache (overwrite existing for the date)
    games_cache[date] = stored_games

    return {"date": date, "games_fetched": len(stored_games)}

async def notify_subscribers(date: str):
    games = games_cache.get(date, [])
    if not subscribers_cache:
        logger.info("No subscribers to notify.")
        return

    subject = f"NBA Scores for {date}"
    body = format_scores_email(date, games)

    # Ideally send emails concurrently, but here simple send to all as one batch (mock)
    await send_email(list(subscribers_cache), subject, body)
    logger.info(f"Notifications sent to {len(subscribers_cache)} subscribers for {date}")

# --- API Endpoints ---

@app.route("/subscribe", methods=["POST"])
async def subscribe():
    data = await request.get_json(force=True)
    email = data.get("email", "").strip().lower()
    if not email or "@" not in email:
        return jsonify({"error": "Invalid email"}), 400
    if email in subscribers_cache:
        return jsonify({"error": "Email already subscribed"}), 400

    subscribers_cache.add(email)
    logger.info(f"New subscriber added: {email}")
    return jsonify({"message": "Subscribed successfully"}), 201

@app.route("/subscribers", methods=["GET"])
async def get_subscribers():
    return jsonify({"subscribers": list(subscribers_cache)}), 200

@app.route("/games/fetch", methods=["POST"])
async def fetch_scores():
    data = await request.get_json(force=True)
    date_str = data.get("date", "").strip()
    try:
        # Validate date format YYYY-MM-DD
        datetime.strptime(date_str, "%Y-%m-%d")
    except Exception:
        return jsonify({"error": "Invalid date format. Use YYYY-MM-DD"}), 400

    # Fire and forget
    async def process_fetch_and_notify(date: str):
        try:
            result = await fetch_and_store_scores(date)
            await notify_subscribers(date)
            logger.info(f"Fetch and notify completed for {date}")
        except Exception as e:
            logger.exception(f"Error in fetch and notify task for {date}: {e}")

    asyncio.create_task(process_fetch_and_notify(date_str))

    return jsonify({"message": f"Fetch and notification started for {date_str}"}), 200

@app.route("/games/all", methods=["GET"])
async def get_all_games():
    all_games = []
    for date, games in games_cache.items():
        all_games.extend(games)
    return jsonify({"games": all_games}), 200

@app.route("/games/<date>", methods=["GET"])
async def get_games_by_date(date: str):
    try:
        datetime.strptime(date, "%Y-%m-%d")
    except Exception:
        return jsonify({"error": "Invalid date format. Use YYYY-MM-DD"}), 400

    games = games_cache.get(date, [])
    return jsonify({"date": date, "games": games}), 200

# --- Background Scheduler ---

async def daily_fetch_scheduler():
    """Simple scheduler that runs every minute and triggers fetch at 18:00 UTC."""
    while True:
        now = datetime.utcnow()
        if now.hour == 18 and now.minute == 0:
            date_str = now.strftime("%Y-%m-%d")
            logger.info(f"Scheduler triggered fetch for {date_str}")
            try:
                await fetch_and_store_scores(date_str)
                await notify_subscribers(date_str)
                logger.info(f"Scheduled fetch and notify completed for {date_str}")
            except Exception as e:
                logger.exception(f"Scheduled fetch/notify failed: {e}")
            # Sleep 61 seconds to avoid multiple triggers within same minute
            await asyncio.sleep(61)
        else:
            await asyncio.sleep(10)  # Check every 10 seconds

@app.before_serving
async def startup_tasks():
    # Start scheduler task in background
    asyncio.create_task(daily_fetch_scheduler())
    logger.info("Background scheduler started")

if __name__ == '__main__':
    import sys
    import logging

    # Basic console logging
    logging.basicConfig(
        stream=sys.stdout,
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s"
    )

    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
```
