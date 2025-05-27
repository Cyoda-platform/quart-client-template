```python
import asyncio
import logging
from datetime import date
from typing import Dict, List

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# In-memory "databases"
_subscribers: List[str] = []
_games_by_date: Dict[str, List[Dict]] = {}

API_KEY = "test"
NBA_API_URL = "https://api.sportsdata.io/v3/nba/scores/json/ScoresBasicFinal/{date}?key={key}"

# -------------------------
# Helper async functions
# -------------------------

async def fetch_nba_scores(fetch_date: str) -> List[Dict]:
    url = NBA_API_URL.format(date=fetch_date, key=API_KEY)
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(url, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            # TODO: Validate / normalize data structure if needed
            return data
        except Exception as e:
            logger.exception(f"Failed to fetch NBA scores for {fetch_date}: {e}")
            return []

async def send_email(to_emails: List[str], subject: str, body: str):
    # TODO: Implement actual email sending (SMTP, SendGrid, etc.)
    # For now, just log the email sending simulation
    logger.info(f"Sending email to {to_emails}: {subject}\n{body}")

def format_scores_summary(games: List[Dict]) -> str:
    if not games:
        return "No games found for this date."
    lines = []
    for game in games:
        lines.append(
            f"{game.get('AwayTeam', 'N/A')} @ {game.get('HomeTeam', 'N/A')}: "
            f"{game.get('AwayTeamScore', 'N/A')} - {game.get('HomeTeamScore', 'N/A')} "
            f"({game.get('Status', 'N/A')})"
        )
    return "\n".join(lines)

# -------------------------
# Background processing job
# -------------------------

async def process_fetch_and_notify(fetch_date: str):
    logger.info(f"Starting fetch and notify for {fetch_date}")
    games = await fetch_nba_scores(fetch_date)
    _games_by_date[fetch_date] = games

    subscribers = list(_subscribers)  # snapshot to avoid concurrency issues
    if not subscribers:
        logger.info("No subscribers to notify.")
        return

    summary = format_scores_summary(games)
    subject = f"NBA Scores for {fetch_date}"
    await send_email(subscribers, subject, summary)
    logger.info(f"Finished sending notifications for {fetch_date}")

# -------------------------
# API endpoints
# -------------------------

@app.route("/subscribe", methods=["POST"])
async def subscribe():
    data = await request.get_json(force=True)
    email = data.get("email")
    if not email or not isinstance(email, str):
        return jsonify({"error": "Invalid or missing 'email' field"}), 400

    if email not in _subscribers:
        _subscribers.append(email)
        logger.info(f"New subscriber added: {email}")
    else:
        logger.info(f"Subscriber {email} already exists.")

    return jsonify({"message": "Subscription successful", "email": email})

@app.route("/fetch-scores", methods=["POST"])
async def fetch_scores():
    data = await request.get_json(force=True)
    fetch_date = data.get("date")
    if not fetch_date:
        return jsonify({"error": "Missing 'date' field"}), 400

    # Fire and forget the processing task
    asyncio.create_task(process_fetch_and_notify(fetch_date))

    return jsonify({
        "message": "Scores fetch initiated",
        "date": fetch_date
    })

@app.route("/subscribers", methods=["GET"])
async def get_subscribers():
    return jsonify({"subscribers": list(_subscribers)})

@app.route("/games/all", methods=["GET"])
async def get_all_games():
    all_games = []
    for games in _games_by_date.values():
        all_games.extend(games)
    return jsonify({"games": all_games})

@app.route("/games/<string:fetch_date>", methods=["GET"])
async def get_games_by_date(fetch_date):
    games = _games_by_date.get(fetch_date, [])
    return jsonify({"games": games})

# -------------------------
# Scheduler Simulation
# -------------------------

async def daily_scheduler():
    """
    Simulates a daily scheduler that fetches today's NBA scores at 6:00 PM UTC.
    For prototype purposes, runs once after startup with today's date.
    """
    await asyncio.sleep(1)  # Delay startup a bit
    today = date.today().isoformat()
    logger.info(f"Scheduler triggered fetch for {today}")
    await process_fetch_and_notify(today)

@app.before_serving
async def startup():
    # Start scheduler task (simulate daily fetch)
    asyncio.create_task(daily_scheduler())

# -------------------------
# Entry point
# -------------------------

if __name__ == '__main__':
    import sys
    import logging

    logging.basicConfig(
        level=logging.INFO,
        format='[%(asctime)s] %(levelname)s in %(module)s: %(message)s'
    )
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
```
