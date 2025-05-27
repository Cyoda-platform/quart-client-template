from dataclasses import dataclass
import asyncio
import logging
from datetime import date
from typing import Dict, List

import httpx
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

# Data models for requests
@dataclass
class SubscribeRequest:
    email: str

@dataclass
class FetchScoresRequest:
    date: str

entity_name = "subscriber"
games_entity_name = "game"

API_KEY = "test"
NBA_API_URL = "https://api.sportsdata.io/v3/nba/scores/json/ScoresBasicFinal/{date}?key={key}"

# Helper async functions
async def fetch_nba_scores(fetch_date: str) -> List[Dict]:
    url = NBA_API_URL.format(date=fetch_date, key=API_KEY)
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(url, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            return data
        except Exception as e:
            logger.exception(f"Failed to fetch NBA scores for {fetch_date}: {e}")
            return []

async def send_email(to_emails: List[str], subject: str, body: str):
    # TODO: Implement actual email sending (SMTP, SendGrid, etc.)
    logger.info(f"Sending email to {to_emails}: {subject}\n{body}")

def format_scores_summary(games: List[Dict]) -> str:
    if not games:
        return "No games found for this date."
    lines = []
    for game in games:
        lines.append(
            f"{game.get('AwayTeam','N/A')} @ {game.get('HomeTeam','N/A')}: "
            f"{game.get('AwayTeamScore','N/A')} - {game.get('HomeTeamScore','N/A')} "
            f"({game.get('Status','N/A')})"
        )
    return "\n".join(lines)

# Background processing job
async def process_fetch_and_notify(fetch_date: str):
    logger.info(f"Starting fetch and notify for {fetch_date}")
    games = await fetch_nba_scores(fetch_date)
    # Store games using entity_service - add or update by technical_id as fetch_date (string)
    try:
        # Try to get existing item
        existing = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model=games_entity_name,
            entity_version=ENTITY_VERSION,
            technical_id=fetch_date
        )
        # Update existing
        await entity_service.update_item(
            token=cyoda_auth_service,
            entity_model=games_entity_name,
            entity_version=ENTITY_VERSION,
            entity=games,
            technical_id=fetch_date,
            meta={}
        )
    except Exception:
        # If not found or error, add new item with technical_id = fetch_date
        # The add_item returns a new id, but we want to store with fetch_date as id,
        # so skipping add_item, just leaving as is if not possible.
        pass

    # Get subscribers list from entity_service
    try:
        subs = await entity_service.get_items(
            token=cyoda_auth_service,
            entity_model=entity_name,
            entity_version=ENTITY_VERSION,
        )
        subscribers = [item.get("email") for item in subs if "email" in item]
    except Exception as e:
        logger.exception(f"Failed to retrieve subscribers: {e}")
        subscribers = []

    if not subscribers:
        logger.info("No subscribers to notify.")
        return

    summary = format_scores_summary(games)
    subject = f"NBA Scores for {fetch_date}"
    await send_email(subscribers, subject, summary)
    logger.info(f"Finished sending notifications for {fetch_date}")

# API endpoints

@app.route("/subscribe", methods=["POST"])
@validate_request(SubscribeRequest)
async def subscribe(data: SubscribeRequest):
    email = data.email
    # Check if subscriber exists by condition
    condition = {
        "cyoda": {
            "type": "group",
            "operator": "AND",
            "conditions": [
                {
                    "jsonPath": "$.email",
                    "operatorType": "EQUALS",
                    "value": email,
                    "type": "simple"
                }
            ]
        }
    }
    try:
        existing = await entity_service.get_items_by_condition(
            token=cyoda_auth_service,
            entity_model=entity_name,
            entity_version=ENTITY_VERSION,
            condition=condition
        )
        if existing:
            logger.info(f"Subscriber {email} already exists.")
            return jsonify({"message": "Subscription successful", "email": email})
        # Add new subscriber
        new_id = await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model=entity_name,
            entity_version=ENTITY_VERSION,
            entity={"email": email}
        )
        logger.info(f"New subscriber added: {email} with id {new_id}")
        return jsonify({"message": "Subscription successful", "email": email})
    except Exception as e:
        logger.exception(e)
        return jsonify({"message": "Failed to subscribe"}), 500

@app.route("/fetch-scores", methods=["POST"])
@validate_request(FetchScoresRequest)
async def fetch_scores(data: FetchScoresRequest):
    fetch_date = data.date
    asyncio.create_task(process_fetch_and_notify(fetch_date))
    return jsonify({"message": "Scores fetch initiated", "date": fetch_date})

@app.route("/subscribers", methods=["GET"])
async def get_subscribers():
    try:
        items = await entity_service.get_items(
            token=cyoda_auth_service,
            entity_model=entity_name,
            entity_version=ENTITY_VERSION,
        )
        return jsonify({"subscribers": items})
    except Exception as e:
        logger.exception(e)
        return jsonify({"subscribers": []})

@app.route("/games/all", methods=["GET"])
async def get_all_games():
    try:
        items = await entity_service.get_items(
            token=cyoda_auth_service,
            entity_model=games_entity_name,
            entity_version=ENTITY_VERSION,
        )
        all_games = []
        for games in items:
            if isinstance(games, list):
                all_games.extend(games)
            else:
                all_games.append(games)
        return jsonify({"games": all_games})
    except Exception as e:
        logger.exception(e)
        return jsonify({"games": []})

@app.route("/games/<string:fetch_date>", methods=["GET"])
async def get_games_by_date(fetch_date):
    try:
        games = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model=games_entity_name,
            entity_version=ENTITY_VERSION,
            technical_id=fetch_date
        )
        return jsonify({"games": games})
    except Exception as e:
        logger.exception(e)
        return jsonify({"games": []})

# Scheduler Simulation
async def daily_scheduler():
    await asyncio.sleep(1)
    today = date.today().isoformat()
    logger.info(f"Scheduler triggered fetch for {today}")
    await process_fetch_and_notify(today)

@app.before_serving
async def startup():
    asyncio.create_task(daily_scheduler())

if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='[%(asctime)s] %(levelname)s in %(module)s: %(message)s'
    )
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)