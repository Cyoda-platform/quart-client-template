from dataclasses import dataclass
import asyncio
import logging
from datetime import datetime
from typing import Dict, List

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request

from app_init.app_init import BeanFactory
from common.config.config import ENTITY_VERSION

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

factory = BeanFactory(config={'CHAT_REPOSITORY': 'cyoda'})
entity_service = factory.get_services()['entity_service']
cyoda_auth_service = factory.get_services()["cyoda_auth_service"]

app = Quart(__name__)
QuartSchema(app)

@dataclass
class SubscribeRequest:
    email: str

@dataclass
class FetchRequest:
    date: str

ENTITY_NAME = "subscriber"
GAME_ENTITY_NAME = "game"

API_KEY = "test"
API_URL_TEMPLATE = "https://api.sportsdata.io/v3/nba/scores/json/ScoresBasicFinal/{date}?key=" + API_KEY

async def process_subscriber(entity: Dict) -> None:
    if "email" in entity and entity["email"]:
        entity["email"] = entity["email"].strip().lower()
    async def send_welcome_email(email: str):
        try:
            logger.info(f"Sending welcome email to {email}")
            # Replace with real email sending logic
            await asyncio.sleep(0.1)
        except Exception as e:
            logger.warning(f"Failed to send welcome email to {email}: {e}")
    asyncio.create_task(send_welcome_email(entity["email"]))
    logger.debug(f"Processed subscriber entity: {entity}")

async def process_game(entity: Dict) -> None:
    entity["processed_at"] = datetime.utcnow().isoformat() + "Z"
    logger.debug(f"Processed game entity: {entity}")

async def send_email(to_emails: List[str], subject: str, body: str):
    try:
        logger.info(f"Sending email to {to_emails} with subject {subject}")
        # Replace with actual email sending logic
        await asyncio.sleep(0.1)
    except Exception as e:
        logger.warning(f"Failed to send email to {to_emails}: {e}")

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
            game_data = {
                "date": date,
                "home_team": game.get("HomeTeam"),
                "away_team": game.get("AwayTeam"),
                "home_score": game.get("HomeTeamScore"),
                "away_score": game.get("AwayTeamScore"),
                "status": game.get("Status")
            }
            stored_games.append(game_data)
        except Exception as e:
            logger.warning(f"Skipping invalid game data: {game} ({e})")

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
    try:
        old_games = await entity_service.get_items_by_condition(
            token=cyoda_auth_service,
            entity_model=GAME_ENTITY_NAME,
            entity_version=ENTITY_VERSION,
            condition=condition
        )
        for old_game in old_games:
            tech_id = old_game.get("technical_id")
            if tech_id:
                await entity_service.delete_item(
                    token=cyoda_auth_service,
                    entity_model=GAME_ENTITY_NAME,
                    entity_version=ENTITY_VERSION,
                    technical_id=str(tech_id),
                    meta={}
                )
    except Exception as e:
        logger.warning(f"Could not delete old games for date {date}: {e}")

    for game_data in stored_games:
        try:
            await entity_service.add_item(
                token=cyoda_auth_service,
                entity_model=GAME_ENTITY_NAME,
                entity_version=ENTITY_VERSION,
                entity=game_data
            )
        except Exception as e:
            logger.warning(f"Failed to store game data: {game_data} ({e})")

    return {"date": date, "games_fetched": len(stored_games)}

async def notify_subscribers(date: str):
    try:
        subscribers = await entity_service.get_items(
            token=cyoda_auth_service,
            entity_model=ENTITY_NAME,
            entity_version=ENTITY_VERSION,
        )
        emails = [sub.get("email") for sub in subscribers if sub.get("email")]
        if not emails:
            logger.info("No subscribers to notify.")
            return
    except Exception as e:
        logger.warning(f"Failed to get subscribers: {e}")
        return

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
            entity_model=GAME_ENTITY_NAME,
            entity_version=ENTITY_VERSION,
            condition=condition
        )
    except Exception as e:
        logger.warning(f"Failed to get games for notify: {e}")
        games = []

    subject = f"NBA Scores for {date}"
    body = format_scores_email(date, games)
    await send_email(emails, subject, body)
    logger.info(f"Notifications sent to {len(emails)} subscribers for {date}")

@app.route("/subscribe", methods=["POST"])
@validate_request(SubscribeRequest)
async def subscribe(data: SubscribeRequest):
    email = data.email.strip().lower()
    if not email or "@" not in email:
        return jsonify({"error": "Invalid email"}), 400

    try:
        condition = {
            "cyoda": {
                "type": "group",
                "operator": "AND",
                "conditions": [
                    {
                        "jsonPath": "$.email",
                        "operatorType": "IEQUALS",
                        "value": email,
                        "type": "simple"
                    }
                ]
            }
        }
        existing = await entity_service.get_items_by_condition(
            token=cyoda_auth_service,
            entity_model=ENTITY_NAME,
            entity_version=ENTITY_VERSION,
            condition=condition
        )
        if existing:
            return jsonify({"error": "Email already subscribed"}), 400
    except Exception as e:
        logger.warning(f"Failed to check existing subscriber: {e}")

    try:
        await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model=ENTITY_NAME,
            entity_version=ENTITY_VERSION,
            entity={"email": email}
        )
        logger.info(f"New subscriber added: {email}")
        return jsonify({"message": "Subscribed successfully"}), 201
    except Exception as e:
        logger.exception(f"Failed to add subscriber: {e}")
        return jsonify({"error": "Failed to subscribe"}), 500

@app.route("/games/fetch", methods=["POST"])
@validate_request(FetchRequest)
async def fetch_scores(data: FetchRequest):
    date_str = data.date.strip()
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
    except Exception:
        return jsonify({"error": "Invalid date format. Use YYYY-MM-DD"}), 400

    async def process_fetch():
        try:
            await fetch_and_store_scores(date_str)
            await notify_subscribers(date_str)
            logger.info(f"Fetch and notify completed for {date_str}")
        except Exception as e:
            logger.exception(f"Error in fetch and notify task for {date_str}: {e}")

    asyncio.create_task(process_fetch())
    return jsonify({"message": f"Fetch and notification started for {date_str}"}), 200

@app.route("/subscribers", methods=["GET"])
async def get_subscribers():
    try:
        subscribers = await entity_service.get_items(
            token=cyoda_auth_service,
            entity_model=ENTITY_NAME,
            entity_version=ENTITY_VERSION,
        )
        return jsonify({"subscribers": [sub.get("email") for sub in subscribers if sub.get("email")]}, 200)
    except Exception as e:
        logger.exception(f"Failed to get subscribers: {e}")
        return jsonify({"error": "Failed to retrieve subscribers"}), 500

@app.route("/games/all", methods=["GET"])
async def get_all_games():
    try:
        games = await entity_service.get_items(
            token=cyoda_auth_service,
            entity_model=GAME_ENTITY_NAME,
            entity_version=ENTITY_VERSION,
        )
        return jsonify({"games": games}), 200
    except Exception as e:
        logger.exception(f"Failed to get all games: {e}")
        return jsonify({"error": "Failed to retrieve games"}), 500

@app.route("/games/<date>", methods=["GET"])
async def get_games_by_date(date: str):
    try:
        datetime.strptime(date, "%Y-%m-%d")
    except Exception:
        return jsonify({"error": "Invalid date format. Use YYYY-MM-DD"}), 400
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
    try:
        games = await entity_service.get_items_by_condition(
            token=cyoda_auth_service,
            entity_model=GAME_ENTITY_NAME,
            entity_version=ENTITY_VERSION,
            condition=condition
        )
        return jsonify({"date": date, "games": games}), 200
    except Exception as e:
        logger.exception(f"Failed to get games by date: {e}")
        return jsonify({"error": "Failed to retrieve games"}), 500

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
