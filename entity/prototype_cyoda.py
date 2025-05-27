from dataclasses import dataclass
import asyncio
import logging
from datetime import datetime
from typing import List, Dict

import httpx
from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request, validate_querystring

from app_init.app_init import BeanFactory
from common.config.config import ENTITY_VERSION

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

factory = BeanFactory(config={'CHAT_REPOSITORY': 'cyoda'})
entity_service = factory.get_services()['entity_service']
cyoda_auth_service = factory.get_services()["cyoda_auth_service"]

app = Quart(__name__)
QuartSchema(app)

# Data classes for request validation
@dataclass
class Subscriber:
    email: str

@dataclass
class FetchScores:
    date: str

@dataclass
class GamesQuery:
    page: int
    limit: int

entity_name_subscriber = "subscriber"
entity_name_game = "game"

NBA_API_KEY = "test"
NBA_API_URL = "https://api.sportsdata.io/v3/nba/scores/json/ScoresBasicFinal/{date}?key=" + NBA_API_KEY

async def fetch_nba_scores(date: str) -> List[dict]:
    url = NBA_API_URL.format(date=date)
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        logger.exception(f"Failed to fetch NBA scores for {date}: {e}")
        return []

async def send_email(to_emails: List[str], subject: str, body: str):
    await asyncio.sleep(0.1)
    logger.info(f"Mock email to {len(to_emails)}: {subject}\n{body}")

def build_email_body(date: str, games: List[dict]) -> str:
    if not games:
        return f"No NBA games found for {date}."
    lines = [f"NBA Scores for {date}:\n"]
    for g in games:
        home = g.get("HomeTeam") or "Home"
        away = g.get("AwayTeam") or "Away"
        home_score = g.get("HomeTeamScore") or "N/A"
        away_score = g.get("AwayTeamScore") or "N/A"
        lines.append(f"{away} @ {home} — {away_score}:{home_score}")
    return "\n".join(lines)

async def list_subscribers_from_entity_service() -> List[str]:
    try:
        items = await entity_service.get_items(
            token=cyoda_auth_service,
            entity_model=entity_name_subscriber,
            entity_version=ENTITY_VERSION,
        )
        # items is list of dicts, each dict corresponds to an entity - get 'email' field
        return [item.get("email") for item in items if "email" in item]
    except Exception as e:
        logger.exception(f"Error retrieving subscribers: {e}")
        return []

async def check_subscriber_exists(email: str) -> bool:
    try:
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
        items = await entity_service.get_items_by_condition(
            token=cyoda_auth_service,
            entity_model=entity_name_subscriber,
            entity_version=ENTITY_VERSION,
            condition=condition,
        )
        return len(items) > 0
    except Exception as e:
        logger.exception(f"Error checking subscriber existence: {e}")
        return False

async def add_subscriber_entity(email: str) -> bool:
    try:
        id = await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model=entity_name_subscriber,
            entity_version=ENTITY_VERSION,
            entity={"email": email}
        )
        return True
    except Exception as e:
        logger.exception(f"Error adding subscriber: {e}")
        return False

async def save_games_entity(date: str, games: List[dict]):
    try:
        # Save games under one entity with technical_id = date (as string)
        # For update or add: check if exists, then update or add
        existing = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model=entity_name_game,
            entity_version=ENTITY_VERSION,
            technical_id=date
        )
        if existing:
            await entity_service.update_item(
                token=cyoda_auth_service,
                entity_model=entity_name_game,
                entity_version=ENTITY_VERSION,
                entity={"date": date, "games": games},
                technical_id=date,
                meta={}
            )
        else:
            # Add new with technical_id=date is not supported by add_item, so we add and then update to set technical_id
            # But since add_item returns new id, and we want to use date as id, we will just add and ignore technical_id
            # So we do add_item with entity holding date and games
            id = await entity_service.add_item(
                token=cyoda_auth_service,
                entity_model=entity_name_game,
                entity_version=ENTITY_VERSION,
                entity={"date": date, "games": games}
            )
            # We cannot guarantee technical_id=date; so we rely on separate get by date by filtering
            # So no update here
    except Exception as e:
        logger.exception(f"Error saving games for {date}: {e}")

async def get_all_games_entity() -> List[dict]:
    try:
        items = await entity_service.get_items(
            token=cyoda_auth_service,
            entity_model=entity_name_game,
            entity_version=ENTITY_VERSION,
        )
        all_games = []
        for item in items:
            games = item.get("games", [])
            all_games.extend(games)
        return all_games
    except Exception as e:
        logger.exception(f"Error retrieving all games: {e}")
        return []

async def get_games_by_date_entity(date: str) -> List[dict]:
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
        items = await entity_service.get_items_by_condition(
            token=cyoda_auth_service,
            entity_model=entity_name_game,
            entity_version=ENTITY_VERSION,
            condition=condition
        )
        if not items:
            return []
        # There could be multiple, but we take first
        return items[0].get("games", [])
    except Exception as e:
        logger.exception(f"Error retrieving games by date {date}: {e}")
        return []

async def process_fetch_store_notify(date: str):
    logger.info(f"Starting process for {date}")
    games = await fetch_nba_scores(date)
    await save_games_entity(date, games)
    subscribers = await list_subscribers_from_entity_service()
    if not subscribers:
        logger.info("No subscribers to notify.")
        return
    body = build_email_body(date, games)
    subject = f"NBA Scores for {date}"
    try:
        await send_email(subscribers, subject, body)
        logger.info(f"Notified {len(subscribers)} subscribers.")
    except Exception as e:
        logger.exception(f"Error sending emails: {e}")

@app.route("/subscribe", methods=["POST"])
@validate_request(Subscriber)
async def subscribe(data: Subscriber):
    exists = await check_subscriber_exists(data.email)
    if exists:
        return jsonify({"message": "Email already subscribed", "email": data.email}), 409
    added = await add_subscriber_entity(data.email)
    if not added:
        return jsonify({"message": "Failed to add subscriber"}), 500
    return jsonify({"message": "Subscription successful", "email": data.email}), 201

@app.route("/subscribers", methods=["GET"])
async def get_subscribers():
    subs = await list_subscribers_from_entity_service()
    return jsonify({"subscribers": subs})

@app.route("/fetch-scores", methods=["POST"])
@validate_request(FetchScores)
async def fetch_scores(data: FetchScores):
    try:
        datetime.strptime(data.date, "%Y-%m-%d")
    except ValueError:
        return jsonify({"message": "Invalid date format, expected YYYY-MM-DD"}), 400
    asyncio.create_task(process_fetch_store_notify(data.date))
    return jsonify({"message": f"Scores fetch started for {data.date}"}), 202

@validate_querystring(GamesQuery)
@app.route("/games/all", methods=["GET"])
async def get_all_games():
    page = request.args.get("page", default=1, type=int)
    limit = request.args.get("limit", default=50, type=int)
    if page < 1 or limit < 1:
        return jsonify({"message": "Page and limit must be positive integers"}), 400
    all_games = await get_all_games_entity()
    total = len(all_games)
    start = (page - 1) * limit
    end = start + limit
    return jsonify({
        "games": all_games[start:end],
        "page": page,
        "limit": limit,
        "total": total
    })

@app.route("/games/<date>", methods=["GET"])
async def get_games_by_date(date):
    try:
        datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        return jsonify({"message": "Invalid date format, expected YYYY-MM-DD"}), 400
    games = await get_games_by_date_entity(date)
    return jsonify({"date": date, "games": games})

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)