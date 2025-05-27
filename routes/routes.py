import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import List, Dict, Optional

import httpx
from quart import Blueprint, request, jsonify
from quart_schema import validate_request

from app_init.app_init import BeanFactory
from common.config.config import ENTITY_VERSION

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

factory = BeanFactory(config={'CHAT_REPOSITORY': 'cyoda'})
entity_service = factory.get_services()['entity_service']
cyoda_auth_service = factory.get_services()["cyoda_auth_service"]

routes_bp = Blueprint('routes', __name__)

@dataclass
class EmailBody:
    email: str

@dataclass
class DateBody:
    date: str

ENTITY_NAME = "subscriber"
SCORE_REQUEST_ENTITY = "score_request"

class Storage:
    def __init__(self):
        self._games_by_date: Dict[str, List[Dict]] = {}
        self._lock = asyncio.Lock()

    async def store_games(self, date: str, games: List[Dict]):
        async with self._lock:
            self._games_by_date[date] = games
            logger.info(f"Stored {len(games)} games for date {date}")

    async def get_games_by_date(self, date: str) -> List[Dict]:
        async with self._lock:
            return self._games_by_date.get(date, [])

    async def get_all_games(self, start_date: Optional[str] = None, end_date: Optional[str] = None) -> List[Dict]:
        async with self._lock:
            all_games = []
            for date_str, games in self._games_by_date.items():
                if start_date and date_str < start_date:
                    continue
                if end_date and date_str > end_date:
                    continue
                all_games.extend(games)
            return all_games

storage = Storage()

async def send_email(to_email: str, subject: str, html_content: str):
    logger.info(f"Sending email to {to_email} with subject '{subject}'")
    # Placeholder for real email sending logic
    await asyncio.sleep(0.1)

def build_html_summary(date: str, games: List[Dict]) -> str:
    html = f"<h2>NBA Scores for {date}</h2><ul>"
    for g in games:
        home = g.get("HomeTeam", "N/A")
        away = g.get("AwayTeam", "N/A")
        home_score = g.get("HomeTeamScore", "N/A")
        away_score = g.get("AwayTeamScore", "N/A")
        status = g.get("Status", "")
        html += f"<li>{away} @ {home} : {away_score} - {home_score} ({status})</li>"
    html += "</ul>"
    return html

async def get_subscribers_list() -> List[str]:
    try:
        items = await entity_service.get_items(
            token=cyoda_auth_service,
            entity_model=ENTITY_NAME,
            entity_version=ENTITY_VERSION,
        )
        emails = [item.get("email") for item in items if "email" in item and isinstance(item.get("email"), str)]
        return emails
    except Exception as e:
        logger.exception(f"Failed to get subscribers list: {e}")
        return []

# Workflow function applied to subscriber entity before persistence
async def process_subscriber(entity: Dict) -> Dict:
    if "created_at" not in entity:
        entity["created_at"] = datetime.utcnow().isoformat() + "Z"
    email = entity.get("email")
    if isinstance(email, str):
        entity["email"] = email.strip().lower()
    else:
        entity["email"] = ""
    return entity

# Workflow function applied to score_request entity before persistence
async def process_score_request(entity: Dict) -> Dict:
    date = entity.get("date")
    if not date or not isinstance(date, str):
        entity["fetch_status"] = "failed"
        entity["error"] = "Missing or invalid 'date' field"
        logger.error("Score request entity missing valid date")
        return entity

    try:
        datetime.strptime(date, "%Y-%m-%d")
    except Exception:
        entity["fetch_status"] = "failed"
        entity["error"] = "Invalid date format, expected YYYY-MM-DD"
        logger.error(f"Score request entity has invalid date format: {date}")
        return entity

    API_KEY = "test"
    NBA_API_URL_TEMPLATE = "https://api.sportsdata.io/v3/nba/scores/json/ScoresBasicFinal/{date}?key=" + API_KEY

    try:
        url = NBA_API_URL_TEMPLATE.format(date=date)
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            games = resp.json()
            if not isinstance(games, list):
                raise ValueError("Unexpected response format: expected list of games")
    except Exception as e:
        logger.exception(f"Failed to fetch NBA scores for {date}: {e}")
        entity["fetch_status"] = "failed"
        entity["error"] = str(e)
        return entity

    try:
        await storage.store_games(date, games)
    except Exception as e:
        logger.exception(f"Failed to store games locally for {date}: {e}")
        entity["fetch_status"] = "failed"
        entity["error"] = f"Storage error: {e}"
        return entity

    subscribers = await get_subscribers_list()
    num_subscribers = len(subscribers)

    summary_html = build_html_summary(date, games) if num_subscribers > 0 else ""

    async def safe_send(email):
        try:
            await send_email(email, f"NBA Scores for {date}", summary_html)
        except Exception as ex:
            logger.warning(f"Failed to send email to {email}: {ex}")

    if num_subscribers > 0:
        await asyncio.gather(*(safe_send(email) for email in subscribers))

    entity["games_stored"] = len(games)
    entity["notifications_sent"] = num_subscribers
    entity["fetch_status"] = "success"
    entity["processed_at"] = datetime.utcnow().isoformat() + "Z"
    return entity

@routes_bp.route("/subscribe", methods=["POST"])
@validate_request(EmailBody)
async def subscribe(data: EmailBody):
    try:
        email_lower = data.email.strip().lower()
        condition = {
            "cyoda": {
                "type": "group",
                "operator": "AND",
                "conditions": [
                    {
                        "jsonPath": "$.email",
                        "operatorType": "EQUALS",
                        "value": email_lower,
                        "type": "simple"
                    }
                ]
            }
        }
        existing_items = await entity_service.get_items_by_condition(
            token=cyoda_auth_service,
            entity_model=ENTITY_NAME,
            entity_version=ENTITY_VERSION,
            condition=condition
        )
        if existing_items:
            return jsonify({"message": "Email already subscribed", "email": email_lower}), 200

        entity = {"email": email_lower}
        subscriber_id = await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model=ENTITY_NAME,
            entity_version=ENTITY_VERSION,
            entity=entity
        )
        return jsonify({"message": "Subscription successful", "email": email_lower, "id": subscriber_id}), 201
    except Exception as e:
        logger.exception(f"Subscription failed: {e}")
        return jsonify({"message": "Subscription failed", "email": data.email}), 500

@routes_bp.route("/unsubscribe", methods=["POST"])
@validate_request(EmailBody)
async def unsubscribe(data: EmailBody):
    try:
        email_lower = data.email.strip().lower()
        condition = {
            "cyoda": {
                "type": "group",
                "operator": "AND",
                "conditions": [
                    {
                        "jsonPath": "$.email",
                        "operatorType": "EQUALS",
                        "value": email_lower,
                        "type": "simple"
                    }
                ]
            }
        }
        items = await entity_service.get_items_by_condition(
            token=cyoda_auth_service,
            entity_model=ENTITY_NAME,
            entity_version=ENTITY_VERSION,
            condition=condition
        )
        if not items:
            return jsonify({"message": "Email not found in subscribers", "email": email_lower}), 404

        for item in items:
            tech_id = item.get("id") or item.get("technical_id") or item.get("technicalId")
            if tech_id is None:
                logger.warning(f"Subscriber item missing technical id, skipping delete: {item}")
                continue
            await entity_service.delete_item(
                token=cyoda_auth_service,
                entity_model=ENTITY_NAME,
                entity_version=ENTITY_VERSION,
                technical_id=str(tech_id),
                meta={}
            )
        return jsonify({"message": "Unsubscribed successfully", "email": email_lower}), 200
    except Exception as e:
        logger.exception(f"Unsubscribe failed: {e}")
        return jsonify({"message": "Unsubscribe failed", "email": data.email}), 500

@routes_bp.route("/subscribers", methods=["GET"])
async def get_subscribers():
    try:
        items = await entity_service.get_items(
            token=cyoda_auth_service,
            entity_model=ENTITY_NAME,
            entity_version=ENTITY_VERSION,
        )
        emails = [item.get("email") for item in items if "email" in item and isinstance(item.get("email"), str)]
        return jsonify({"subscribers": emails}), 200
    except Exception as e:
        logger.exception(f"Failed to fetch subscribers: {e}")
        return jsonify({"subscribers": []}), 500

@routes_bp.route("/scores/fetch", methods=["POST"])
@validate_request(DateBody)
async def fetch_scores(data: DateBody):
    try:
        datetime.strptime(data.date, "%Y-%m-%d")
    except ValueError:
        return jsonify({"message": "Invalid date format, expected YYYY-MM-DD"}), 400

    try:
        entity = {"date": data.date}
        score_request_id = await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model=SCORE_REQUEST_ENTITY,
            entity_version=ENTITY_VERSION,
            entity=entity
        )
        return jsonify({"message": "Score fetch request accepted", "id": score_request_id, "date": data.date}), 202
    except Exception as e:
        logger.exception(f"Failed to initiate score fetch: {e}")
        return jsonify({"message": "Failed to initiate score fetch", "date": data.date}), 500

@routes_bp.route("/games/all", methods=["GET"])
async def get_all_games():
    try:
        page = int(request.args.get("page", 1))
        page_size = int(request.args.get("pageSize", 10))
        start_date = request.args.get("startDate")
        end_date = request.args.get("endDate")
        all_games = await storage.get_all_games(start_date, end_date)
        total = len(all_games)
        start_idx = max((page - 1) * page_size, 0)
        end_idx = start_idx + page_size
        paged_games = all_games[start_idx:end_idx]
        return jsonify({"games": paged_games, "page": page, "pageSize": page_size, "totalGames": total}), 200
    except Exception as e:
        logger.exception(f"Failed to fetch all games: {e}")
        return jsonify({"games": [], "message": "Error fetching games"}), 500

@routes_bp.route("/games/<string:date>", methods=["GET"])
async def get_games_by_date(date):
    try:
        datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        return jsonify({"message": "Invalid date format, expected YYYY-MM-DD"}), 400
    try:
        games = await storage.get_games_by_date(date)
        return jsonify({"date": date, "games": games}), 200
    except Exception as e:
        logger.exception(f"Failed to fetch games for date {date}: {e}")
        return jsonify({"date": date, "games": [], "message": "Error fetching games"}), 500