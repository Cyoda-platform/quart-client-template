from dataclasses import dataclass
import asyncio
import logging
from datetime import date
from typing import Dict, List

import httpx
from quart import Blueprint, jsonify
from quart_schema import validate_request

from app_init.app_init import BeanFactory
from common.config.config import ENTITY_VERSION

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

routes_bp = Blueprint('routes', __name__)

factory = BeanFactory(config={'CHAT_REPOSITORY': 'cyoda'})
entity_service = factory.get_services()['entity_service']
cyoda_auth_service = factory.get_services()["cyoda_auth_service"]

@dataclass
class SubscribeRequest:
    email: str

@dataclass
class FetchScoresRequest:
    date: str

entity_name = "subscriber"
games_entity_name = "game"
game_detail_entity_name = "game_detail"

API_KEY = "test"
NBA_API_URL = "https://api.sportsdata.io/v3/nba/scores/json/ScoresBasicFinal/{date}?key={key}"

async def process_subscriber(entity_data: Dict) -> Dict:
    logger.info(f"[Workflow] Processing subscriber entity before persistence: {entity_data}")
    import datetime
    if "subscribed_at" not in entity_data:
        entity_data["subscribed_at"] = datetime.datetime.utcnow().isoformat()
    # Additional subscriber logic can be added here without modifying subscriber entities
    return entity_data

async def process_game(entity_data: Dict) -> Dict:
    logger.info(f"[Workflow] Processing game entity before persistence: {entity_data}")

    fetch_date = entity_data.get("date")
    if not fetch_date:
        logger.warning("Game entity missing 'date' field; skipping workflow.")
        entity_data["fetch_status"] = "error: missing date field"
        return entity_data

    try:
        async with httpx.AsyncClient() as client:
            url = NBA_API_URL.format(date=fetch_date, key=API_KEY)
            resp = await client.get(url, timeout=10)
            resp.raise_for_status()
            games_data = resp.json()
            if not isinstance(games_data, list):
                logger.warning(f"Unexpected data format from NBA API for date {fetch_date}")
                games_data = []
            logger.info(f"[Workflow] Fetched {len(games_data)} games for date {fetch_date}")
    except Exception as e:
        logger.error(f"[Workflow] Failed to fetch NBA scores for {fetch_date}: {e}")
        entity_data["fetch_status"] = f"error: {str(e)}"
        return entity_data

    # Persist detailed games as separate entity model 'game_detail' with technical_id=fetch_date
    try:
        existing_detail = None
        try:
            existing_detail = await entity_service.get_item(
                token=cyoda_auth_service,
                entity_model=game_detail_entity_name,
                entity_version=ENTITY_VERSION,
                technical_id=fetch_date
            )
        except Exception:
            # Not found is acceptable, continue to add new
            pass
        if existing_detail is not None:
            await entity_service.update_item(
                token=cyoda_auth_service,
                entity_model=game_detail_entity_name,
                entity_version=ENTITY_VERSION,
                entity=games_data,
                technical_id=fetch_date,
                meta={}
            )
            logger.info(f"[Workflow] Updated existing game_detail entity for {fetch_date}")
        else:
            await entity_service.add_item(
                token=cyoda_auth_service,
                entity_model=game_detail_entity_name,
                entity_version=ENTITY_VERSION,
                entity=games_data,
                workflow=None
            )
            logger.info(f"[Workflow] Added new game_detail entity for {fetch_date}")
    except Exception as e:
        logger.error(f"[Workflow] Failed to persist game_detail entity for {fetch_date}: {e}")

    try:
        subscribers = await entity_service.get_items(
            token=cyoda_auth_service,
            entity_model=entity_name,
            entity_version=ENTITY_VERSION,
        )
        emails = [sub.get("email") for sub in subscribers if "email" in sub]
    except Exception as e:
        logger.error(f"[Workflow] Failed to retrieve subscribers: {e}")
        emails = []

    def format_scores_summary(games: List[Dict]) -> str:
        if not games:
            return "No games found for this date."
        lines = []
        for g in games:
            away = g.get('AwayTeam', 'N/A')
            home = g.get('HomeTeam', 'N/A')
            away_score = g.get('AwayTeamScore', 'N/A')
            home_score = g.get('HomeTeamScore', 'N/A')
            status = g.get('Status', 'N/A')
            lines.append(f"{away} @ {home}: {away_score} - {home_score} ({status})")
        return "\n".join(lines)

    summary = format_scores_summary(games_data)
    subject = f"NBA Scores for {fetch_date}"

    async def send_email(to_emails: List[str], subject: str, body: str):
        # Placeholder for actual email sending implementation
        logger.info(f"[Workflow] Sending email to {len(to_emails)} subscribers:\nSubject: {subject}\nBody:\n{body}")

    if emails:
        asyncio.create_task(send_email(emails, subject, summary))
        logger.info(f"[Workflow] Email notification task started for {len(emails)} subscribers")
    else:
        logger.info("[Workflow] No subscribers to notify.")

    entity_data["fetch_status"] = "success"
    entity_data["games_count"] = len(games_data)
    entity_data["notified_subscribers"] = len(emails)

    return entity_data

@routes_bp.route("/subscribe", methods=["POST"])
@validate_request(SubscribeRequest)
async def subscribe(data: SubscribeRequest):
    email = data.email
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

@routes_bp.route("/fetch-scores", methods=["POST"])
@validate_request(FetchScoresRequest)
async def fetch_scores(data: FetchScoresRequest):
    fetch_date = data.date
    try:
        existing = None
        try:
            existing = await entity_service.get_item(
                token=cyoda_auth_service,
                entity_model=games_entity_name,
                entity_version=ENTITY_VERSION,
                technical_id=fetch_date
            )
        except Exception:
            pass
        if existing:
            await entity_service.update_item(
                token=cyoda_auth_service,
                entity_model=games_entity_name,
                entity_version=ENTITY_VERSION,
                entity={"date": fetch_date},
                technical_id=fetch_date,
                meta={}
            )
            logger.info(f"Triggered workflow update for game entity date {fetch_date}")
        else:
            _ = await entity_service.add_item(
                token=cyoda_auth_service,
                entity_model=games_entity_name,
                entity_version=ENTITY_VERSION,
                entity={"date": fetch_date}
            )
            logger.info(f"Triggered workflow add for game entity date {fetch_date}")
        return jsonify({"message": "Scores fetch triggered", "date": fetch_date})
    except Exception as e:
        logger.exception(e)
        return jsonify({"message": "Failed to trigger scores fetch"}), 500

@routes_bp.route("/subscribers", methods=["GET"])
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

@routes_bp.route("/games/all", methods=["GET"])
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

@routes_bp.route("/games/<string:fetch_date>", methods=["GET"])
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