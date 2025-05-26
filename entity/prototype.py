import asyncio
import datetime
import logging
from typing import Dict, List

import httpx
from dataclasses import dataclass
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request, validate_querystring

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

@dataclass
class SubscribeRequest:
    email: str

@dataclass
class DateRequest:
    date: str

def validate_date(date_str: str) -> bool:
    try:
        datetime.datetime.strptime(date_str, "%Y-%m-%d")
        return True
    except Exception:
        return False

async def fetch_nba_scores(date: str) -> List[Dict]:
    url = EXTERNAL_API_URL.format(date=date, key=API_KEY)
    async with httpx.AsyncClient() as client:
        r = await client.get(url)
        r.raise_for_status()
        data = r.json()
        return data if isinstance(data, list) else []

async def send_email_batch(emails: List[str], date: str, games: List[Dict]):
    summary_lines = []
    for game in games:
        summary_lines.append(
            f"{game.get('home_team','?')} {game.get('home_score','?')} - "
            f"{game.get('away_team','?')} {game.get('away_score','?')}"
        )
    summary = "\n".join(summary_lines) or "No games found."
    for email in emails:
        logger.info(f"Sending email to {email} for {date}:\n{summary}")
    await asyncio.sleep(0.1)

async def process_scores_and_notify(date: str):
    job_id = f"job_{date}"
    entity_jobs[job_id] = {"status": "processing", "requestedAt": datetime.datetime.utcnow().isoformat()}
    try:
        games = await fetch_nba_scores(date)
        games_storage[date] = []
        for g in games:
            games_storage[date].append({
                "date": date,
                "home_team": g.get("HomeTeam"),
                "away_team": g.get("AwayTeam"),
                "home_score": g.get("HomeTeamScore"),
                "away_score": g.get("AwayTeamScore"),
            })
        logger.info(f"Fetched and stored {len(games)} games for {date}")
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
@validate_request(SubscribeRequest)  # Workaround: validate_request after route for POST
async def subscribe(data: SubscribeRequest):
    email = data.email
    if not email:
        return jsonify({"error": "Invalid email"}), 400
    if email in subscribers:
        return jsonify({"error": "Email already subscribed"}), 400
    subscribers.append(email)
    logger.info(f"New subscription: {email}")
    return jsonify({"message": f"Subscribed {email} successfully"}), 201

@app.route("/fetch-scores", methods=["POST"])
@validate_request(DateRequest)  # Workaround: validate_request after route for POST
async def fetch_scores(data: DateRequest):
    date = data.date
    if not validate_date(date):
        return jsonify({"error": "Invalid date format"}), 400
    asyncio.create_task(process_scores_and_notify(date))
    return jsonify({"message": f"Fetching scores for {date} started"}), 200

@app.route("/notify", methods=["POST"])
@validate_request(DateRequest)  # Workaround: validate_request after route for POST
async def notify(data: DateRequest):
    date = data.date
    if not validate_date(date):
        return jsonify({"error": "Invalid date format"}), 400
    games = games_storage.get(date)
    if not games:
        return jsonify({"error": "No data for date"}), 404
    if not subscribers:
        return jsonify({"message": "No subscribers"}), 200
    try:
        await send_email_batch(subscribers, date, games)
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to send notifications"}), 500
    return jsonify({"message": f"Notifications sent for {date}"}), 200

@app.route("/subscribers", methods=["GET"])
async def get_subscribers():
    return jsonify({"subscribers": subscribers})

@app.route("/games/all", methods=["GET"])
async def get_all_games():
    all_games = []
    for date_games in games_storage.values():
        all_games.extend(date_games)
    return jsonify({"games": all_games})

@app.route("/games/<date>", methods=["GET"])
async def get_games_by_date(date):
    if not validate_date(date):
        return jsonify({"error": "Invalid date format"}), 400
    games = games_storage.get(date) or []
    return jsonify({"date": date, "games": games})

async def daily_scheduler():
    while True:
        now = datetime.datetime.utcnow()
        target = now.replace(hour=18, minute=0, second=0, microsecond=0)
        if now > target:
            target += datetime.timedelta(days=1)
        await asyncio.sleep((target - now).total_seconds())
        today = target.strftime("%Y-%m-%d")
        await process_scores_and_notify(today)

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.create_task(daily_scheduler())
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)