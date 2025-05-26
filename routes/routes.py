from datetime import timezone, datetime
import logging
from typing import Dict, List
import asyncio
import httpx
from dataclasses import dataclass
from quart import Blueprint, jsonify, request
from quart_schema import validate_request

from app_init.app_init import BeanFactory
from common.config.config import ENTITY_VERSION

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

routes_bp = Blueprint('routes', __name__)

factory = BeanFactory(config={'CHAT_REPOSITORY': 'cyoda'})
entity_service = factory.get_services()['entity_service']
cyoda_auth_service = factory.get_services()["cyoda_auth_service"]

# In-memory storage mocks for subscribers and jobs
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
        datetime.strptime(date_str, "%Y-%m-%d")
        return True
    except Exception:
        return False

# Workflow function for 'game' entity, called before persistence
async def process_game(entity: dict) -> dict:
    home_score = entity.get("home_score")
    away_score = entity.get("away_score")

    if home_score is not None and away_score is not None:
        if home_score > away_score:
            entity["game_status"] = "home_win"
        elif away_score > home_score:
            entity["game_status"] = "away_win"
        else:
            entity["game_status"] = "draw"
    else:
        entity["game_status"] = "pending"

    summary = f"{entity.get('home_team','?')} {home_score if home_score is not None else '?'} - {entity.get('away_team','?')} {away_score if away_score is not None else '?'}"
    summary_entity = {
        "game_date": entity.get("date"),
        "summary": summary,
    }
    try:
        await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model="game_summary",
            entity_version=ENTITY_VERSION,
            entity=summary_entity,
            workflow=None
        )
    except Exception as e:
        logger.warning(f"Failed to add game_summary entity: {e}")

    return entity

async def process_subscriber(entity: dict) -> dict:
    email = entity.get("email")
    if email:
        entity["email"] = email.strip().lower()
    return entity

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
    entity_jobs[job_id] = {"status": "processing", "requestedAt": datetime.utcnow().isoformat()}
    try:
        games_raw = await fetch_nba_scores(date)

        stored_game_ids = []
        for g in games_raw:
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
                logger.exception(f"Error adding game entity: {e}")

        games = []
        for gid in stored_game_ids:
            try:
                game = await entity_service.get_item(
                    token=cyoda_auth_service,
                    entity_model="game",
                    entity_version=ENTITY_VERSION,
                    technical_id=str(gid)
                )
                if game:
                    games.append(game)
            except Exception as e:
                logger.exception(f"Error fetching stored game id {gid}: {e}")

        logger.info(f"Fetched and stored {len(games)} games for {date}")

        if subscribers:
            await send_email_batch(subscribers, date, games)
            logger.info(f"Sent notifications to {len(subscribers)} subscribers for {date}")
        else:
            logger.info("No subscribers to notify.")

        entity_jobs[job_id]["status"] = "completed"
    except Exception as e:
        logger.exception(f"Error in process_scores_and_notify: {e}")
        entity_jobs[job_id]["status"] = "failed"

@routes_bp.route("/subscribe", methods=["POST"])
@validate_request(SubscribeRequest)
async def subscribe(data: SubscribeRequest):
    email = data.email
    if not email:
        return jsonify({"error": "Invalid email"}), 400
    normalized_email = email.strip().lower()
    if normalized_email in subscribers:
        return jsonify({"error": "Email already subscribed"}), 400
    subscribers.append(normalized_email)
    logger.info(f"New subscription: {normalized_email}")
    try:
        await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model="subscriber",
            entity_version=ENTITY_VERSION,
            entity={"email": normalized_email}
        )
    except Exception as e:
        logger.warning(f"Failed to persist subscriber entity: {e}")
    return jsonify({"message": f"Subscribed {normalized_email} successfully"}), 201

@routes_bp.route("/fetch-scores", methods=["POST"])
@validate_request(DateRequest)
async def fetch_scores(data: DateRequest):
    date = data.date
    if not validate_date(date):
        return jsonify({"error": "Invalid date format"}), 400
    asyncio.create_task(process_scores_and_notify(date))
    return jsonify({"message": f"Fetching scores for {date} started"}), 200

@routes_bp.route("/notify", methods=["POST"])
@validate_request(DateRequest)
async def notify(data: DateRequest):
    date = data.date
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
        if not games:
            return jsonify({"error": "No data for date"}), 404
        if not subscribers:
            return jsonify({"message": "No subscribers"}), 200
        await send_email_batch(subscribers, date, games)
    except Exception as e:
        logger.exception(f"Error in notify endpoint: {e}")
        return jsonify({"error": "Failed to send notifications"}), 500
    return jsonify({"message": f"Notifications sent for {date}"}), 200

@routes_bp.route("/subscribers", methods=["GET"])
async def get_subscribers():
    return jsonify({"subscribers": subscribers})

@routes_bp.route("/games/all", methods=["GET"])
async def get_all_games():
    try:
        games = await entity_service.get_items(
            token=cyoda_auth_service,
            entity_model="game",
            entity_version=ENTITY_VERSION,
        )
        return jsonify({"games": games})
    except Exception as e:
        logger.exception(f"Error in get_all_games: {e}")
        return jsonify({"error": "Failed to retrieve games"}), 500

@routes_bp.route("/games/<string:date>", methods=["GET"])
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
        logger.exception(f"Error in get_games_by_date: {e}")
        return jsonify({"error": "Failed to retrieve games"}), 500