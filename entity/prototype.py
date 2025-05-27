from dataclasses import dataclass
import asyncio
import logging
from datetime import datetime
from typing import Dict, List

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# --- Request models ---
@dataclass
class SubscribeRequest:
    email: str

@dataclass
class FetchRequest:
    date: str

# --- Mocked in-memory persistence ---
subscribers_cache: set = set()
games_cache: Dict[str, List[Dict]] = dict()

API_KEY = "test"
API_URL_TEMPLATE = "https://api.sportsdata.io/v3/nba/scores/json/ScoresBasicFinal/{date}?key=" + API_KEY

async def send_email(to_emails: List[str], subject: str, body: str):
    # TODO: Implement real email sending using SMTP or external provider
    logger.info(f"Sending email to {to_emails} with subject {subject}")
    await asyncio.sleep(0.1)

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

    games_cache[date] = stored_games
    return {"date": date, "games_fetched": len(stored_games)}

async def notify_subscribers(date: str):
    games = games_cache.get(date, [])
    if not subscribers_cache:
        logger.info("No subscribers to notify.")
        return

    subject = f"NBA Scores for {date}"
    body = format_scores_email(date, games)
    await send_email(list(subscribers_cache), subject, body)
    logger.info(f"Notifications sent to {len(subscribers_cache)} subscribers for {date}")

# Subscribe endpoint
@app.route("/subscribe", methods=["POST"])
# Workaround: place validation last for POST due to quart-schema defect
@validate_request(SubscribeRequest)
async def subscribe(data: SubscribeRequest):
    email = data.email.strip().lower()
    if not email or "@" not in email:
        return jsonify({"error": "Invalid email"}), 400
    if email in subscribers_cache:
        return jsonify({"error": "Email already subscribed"}), 400

    subscribers_cache.add(email)
    logger.info(f"New subscriber added: {email}")
    return jsonify({"message": "Subscribed successfully"}), 201

# Fetch scores endpoint
@app.route("/games/fetch", methods=["POST"])
# Workaround: place validation last for POST due to quart-schema defect
@validate_request(FetchRequest)
async def fetch_scores(data: FetchRequest):
    date_str = data.date.strip()
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
    except Exception:
        return jsonify({"error": "Invalid date format. Use YYYY-MM-DD"}), 400

    async def process_fetch_and_notify(date: str):
        try:
            await fetch_and_store_scores(date)
            await notify_subscribers(date)
            logger.info(f"Fetch and notify completed for {date}")
        except Exception as e:
            logger.exception(f"Error in fetch and notify task for {date}: {e}")

    asyncio.create_task(process_fetch_and_notify(date_str))
    return jsonify({"message": f"Fetch and notification started for {date_str}"}), 200

@app.route("/subscribers", methods=["GET"])
async def get_subscribers():
    return jsonify({"subscribers": list(subscribers_cache)}), 200

@app.route("/games/all", methods=["GET"])
async def get_all_games():
    all_games = []
    for games in games_cache.values():
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

async def daily_fetch_scheduler():
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
            await asyncio.sleep(61)
        else:
            await asyncio.sleep(10)

@app.before_serving
async def startup_tasks():
    asyncio.create_task(daily_fetch_scheduler())
    logger.info("Background scheduler started")

if __name__ == '__main__':
    import sys
    logging.basicConfig(
        stream=sys.stdout,
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s"
    )
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)