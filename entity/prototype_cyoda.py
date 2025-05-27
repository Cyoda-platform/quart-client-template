import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import List, Dict, Optional

import httpx
from quart import Quart, request, jsonify
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

# Data classes for request validation
@dataclass
class EmailBody:
    email: str

@dataclass
class DateBody:
    date: str

ENTITY_NAME = "subscriber"  # entity name underscore lowercase

# In-memory mock persistence for games still used as no replacement instructions for games
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
                if start_date and date_str < start_date: continue
                if end_date and date_str > end_date: continue
                all_games.extend(games)
            return all_games

storage = Storage()

API_KEY = "test"
NBA_API_URL_TEMPLATE = "https://api.sportsdata.io/v3/nba/scores/json/ScoresBasicFinal/{date}?key=" + API_KEY

async def send_email(to_email: str, subject: str, html_content: str):
    logger.info(f"Sending email to {to_email} with subject '{subject}'")
    # TODO: Implement real email sending
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

async def process_scores_fetch(date: str):
    try:
        url = NBA_API_URL_TEMPLATE.format(date=date)
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, timeout=20)
            resp.raise_for_status()
            games = resp.json()
        await storage.store_games(date, games)
        subscribers = await get_subscribers_list()
        if subscribers:
            summary_html = build_html_summary(date, games)
            await asyncio.gather(*(send_email(email, f"NBA Scores for {date}", summary_html) for email in subscribers))
        return {"gamesStored": len(games), "notificationsSent": len(subscribers)}
    except Exception as e:
        logger.exception(e)
        raise

async def get_subscribers_list() -> List[str]:
    try:
        items = await entity_service.get_items(
            token=cyoda_auth_service,
            entity_model=ENTITY_NAME,
            entity_version=ENTITY_VERSION,
        )
        emails = [item.get("email") for item in items if "email" in item]
        return emails
    except Exception as e:
        logger.exception(e)
        return []

@app.route("/subscribe", methods=["POST"])
@validate_request(EmailBody)
async def subscribe(data: EmailBody):
    # Instead of local storage, add subscriber via entity_service
    try:
        # Check if email already exists
        condition = {
            "cyoda": {
                "type": "group",
                "operator": "AND",
                "conditions": [
                    {
                        "jsonPath": "$.email",
                        "operatorType": "EQUALS",
                        "value": data.email,
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
            return jsonify({"message": "Email already subscribed", "email": data.email}), 200

        id = await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model=ENTITY_NAME,
            entity_version=ENTITY_VERSION,
            entity={"email": data.email}
        )
        return jsonify({"message": "Subscription successful", "email": data.email, "id": id}), 201
    except Exception as e:
        logger.exception(e)
        return jsonify({"message": "Subscription failed", "email": data.email}), 500

@app.route("/unsubscribe", methods=["POST"])
@validate_request(EmailBody)
async def unsubscribe(data: EmailBody):
    try:
        # Find subscriber by email
        condition = {
            "cyoda": {
                "type": "group",
                "operator": "AND",
                "conditions": [
                    {
                        "jsonPath": "$.email",
                        "operatorType": "EQUALS",
                        "value": data.email,
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
            return jsonify({"message": "Email not found in subscribers", "email": data.email}), 404
        # Delete all matching subscribers (usually one)
        for item in items:
            tech_id = item.get("id") or item.get("technical_id") or item.get("technicalId")
            if tech_id is None:
                continue
            await entity_service.delete_item(
                token=cyoda_auth_service,
                entity_model=ENTITY_NAME,
                entity_version=ENTITY_VERSION,
                technical_id=str(tech_id),
                meta={}
            )
        return jsonify({"message": "Unsubscribed successfully", "email": data.email}), 200
    except Exception as e:
        logger.exception(e)
        return jsonify({"message": "Unsubscribe failed", "email": data.email}), 500

@app.route("/subscribers", methods=["GET"])
async def get_subscribers():
    try:
        items = await entity_service.get_items(
            token=cyoda_auth_service,
            entity_model=ENTITY_NAME,
            entity_version=ENTITY_VERSION,
        )
        emails = [item.get("email") for item in items if "email" in item]
        return jsonify({"subscribers": emails}), 200
    except Exception as e:
        logger.exception(e)
        return jsonify({"subscribers": []}), 500

@app.route("/scores/fetch", methods=["POST"])
@validate_request(DateBody)
async def fetch_scores(data: DateBody):
    try:
        datetime.strptime(data.date, "%Y-%m-%d")
    except ValueError:
        return jsonify({"message": "Invalid date format, expected YYYY-MM-DD"}), 400
    try:
        result = await process_scores_fetch(data.date)
        return jsonify({"message": "Scores fetched and notifications sent", "date": data.date, **result}), 200
    except Exception:
        return jsonify({"message": "Failed to fetch or process scores"}), 500

@app.route("/games/all", methods=["GET"])
async def get_all_games():
    page = int(request.args.get("page", 1))
    page_size = int(request.args.get("pageSize", 10))
    start_date = request.args.get("startDate")
    end_date = request.args.get("endDate")
    all_games = await storage.get_all_games(start_date, end_date)
    total = len(all_games)
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    return jsonify({"games": all_games[start_idx:end_idx], "page": page, "pageSize": page_size, "totalGames": total}), 200

@app.route("/games/<string:date>", methods=["GET"])
async def get_games_by_date(date):
    try:
        datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        return jsonify({"message": "Invalid date format, expected YYYY-MM-DD"}), 400
    games = await storage.get_games_by_date(date)
    return jsonify({"date": date, "games": games}), 200

if __name__ == '__main__':
    import sys
    logging.basicConfig(stream=sys.stdout, level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)