import asyncio
import datetime
import logging
from typing import Dict, List

import httpx
from dataclasses import dataclass
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request, validate_querystring

from app_init.app_init import BeanFactory
from common.config.config import ENTITY_VERSION

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

factory = BeanFactory(config={'CHAT_REPOSITORY': 'cyoda'})
entity_service = factory.get_services()['entity_service']
cyoda_auth_service = factory.get_services()["cyoda_auth_service"]

# In-memory storage mocks
subscribers: List[str] = []
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
        # Store each game as an entity via entity_service
        # First delete existing games for date to avoid duplicates - no delete support by condition given, so skipping
        # Instead, just store games locally for notification, but store entities using entity_service
        stored_game_ids = []
        for g in games:
            data = {
                "date": date,
                "home_team": g.get("HomeTeam"),
                "away_team": g.get("AwayTeam"),
                "home_score": g.get("HomeTeamScore"),
                "away_score": g.get("AwayTeamScore"),
            }
            try:
                game_id = await entity_service.add_item(
                    token=cyoda_auth_service,
                    entity_model="game",
                    entity_version=ENTITY_VERSION,
                    entity=data
                )
                stored_game_ids.append(game_id)
            except Exception as e:
                logger.exception(e)
        # Retrieve stored games by IDs for notification
        games_storage = []
        for gid in stored_game_ids:
            try:
                game = await entity_service.get_item(
                    token=cyoda_auth_service,
                    entity_model="game",
                    entity_version=ENTITY_VERSION,
                    technical_id=str(gid)
                )
                if game:
                    games_storage.append(game)
            except Exception as e:
                logger.exception(e)
        logger.info(f"Fetched and stored {len(games_storage)} games for {date}")
        if subscribers:
            await send_email_batch(subscribers, date, games_storage)
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
    try:
        # Retrieve games by condition date==date
        condition = {
            "cyoda": {
                "type": "group",
                "operator": "AND",
                "conditions": [
                    {
                        "jsonPath": "$.date",
                        "operatorType": "EQUALS",
                        "value": date,
                        "type": "simple"
                    }
                ]
            }
        }
        games = await entity_service.get_items_by_condition(
            token=cyoda_auth_service,
            entity_model="game",
            entity_version=ENTITY_VERSION,
            condition=condition
        )
        if not games:
            return jsonify({"error": "No data for date"}), 404
        if not subscribers:
            return jsonify({"message": "No subscribers"}), 200
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
    try:
        games = await entity_service.get_items(
            token=cyoda_auth_service,
            entity_model="game",
            entity_version=ENTITY_VERSION,
        )
        return jsonify({"games": games})
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to retrieve games"}), 500

@app.route("/games/<string:date>", methods=["GET"])
async def get_games_by_date(date):
    if not validate_date(date):
        return jsonify({"error": "Invalid date format"}), 400
    try:
        condition = {
            "cyoda": {
                "type": "group",
                "operator": "AND",
                "conditions": [
                    {
                        "jsonPath": "$.date",
                        "operatorType": "EQUALS",
                        "value": date,
                        "type": "simple"
                    }
                ]
            }
        }
        games = await entity_service.get_items_by_condition(
            token=cyoda_auth_service,
            entity_model="game",
            entity_version=ENTITY_VERSION,
            condition=condition
        )
        return jsonify({"date": date, "games": games or []})
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to retrieve games"}), 500

async def daily_scheduler():
    while True:
        now = datetime.datetime.utcnow()
        target = now.replace(hour=18, minute=0, second=0, microsecond=0)
        if now > target:
            target += datetime.timedelta(days=1)
        await asyncio.sleep((target - now).total_seconds())
        today = target.strftime("%Y-%m-%d")
        await process_scores_and_notify(today)

# Start scheduler task before serving
@app.before_serving
async def startup():
    app.add_background_task(daily_scheduler)

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)