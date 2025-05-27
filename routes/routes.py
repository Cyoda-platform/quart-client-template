from dataclasses import dataclass
import asyncio
import datetime
import logging
from typing import Dict, List

import httpx
from quart import Quart, jsonify
from quart_schema import QuartSchema, validate_request, validate_querystring

from app_init.app_init import BeanFactory
from common.config.config import ENTITY_VERSION

factory = BeanFactory(config={'CHAT_REPOSITORY': 'cyoda'})
entity_service = factory.get_services()['entity_service']
cyoda_auth_service = factory.get_services()["cyoda_auth_service"]

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# In-memory subscribers list
_subscribers: List[str] = []

@dataclass
class FetchScoresParams:
    date: str

@dataclass
class SubscribeParams:
    email: str

@dataclass
class GamesAllQuery:
    page: int = 1
    limit: int = 100

async def fetch_scores_from_external_api(date: str) -> List[Dict]:
    API_KEY = "test"
    NBA_API_URL = "https://api.sportsdata.io/v3/nba/scores/json/ScoresBasicFinal/{date}?key=" + API_KEY
    url = NBA_API_URL.format(date=date)
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(url, timeout=10.0)
            resp.raise_for_status()
            return resp.json()
        except (httpx.HTTPError, httpx.RequestError) as e:
            logger.exception(f"Failed fetching scores for {date}: {e}")
            return []

async def send_email_to_subscribers(date: str, games: List[Dict]):
    summary_lines = [
        f"{g.get('HomeTeam','N/A')} {g.get('HomeTeamScore','?')} - {g.get('AwayTeam','N/A')} {g.get('AwayTeamScore','?')}"
        for g in games
    ]
    summary = f"NBA Scores for {date}:\n" + "\n".join(summary_lines)
    for email in _subscribers:
        logger.info(f"Sending email to {email}:\n{summary}")
        # TODO: Replace with real email sending logic

# Workflow function for games_by_date entity
async def process_games_by_date_fetch(entity: Dict) -> Dict:
    date = entity.get("date")
    if not date:
        logger.warning("Entity missing 'date' key in workflow")
        return entity
    games = await fetch_scores_from_external_api(date)
    entity['games'] = games
    entity['processedAt'] = datetime.datetime.utcnow().isoformat()
    if _subscribers and games:
        await send_email_to_subscribers(date, games)
    return entity

@app.route("/fetch-scores", methods=["POST"])
@validate_request(FetchScoresParams)
async def fetch_scores(data: FetchScoresParams):
    date = data.date
    try:
        datetime.datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        return jsonify({"status":"error","message":"Invalid date format, expected YYYY-MM-DD"}), 400
    try:
        entity_id = await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model="games_by_date",
            entity_version=ENTITY_VERSION,
            entity={"date": date}
        )
    except Exception as e:
        logger.exception(f"Failed to add entity for date {date}: {e}")
        return jsonify({"status":"error","message":"Failed to start fetch process"}), 500
    return jsonify({"status": "success", "message": "Fetch started", "entity_id": entity_id})

@app.route("/subscribe", methods=["POST"])
@validate_request(SubscribeParams)
async def subscribe(data: SubscribeParams):
    email = data.email.lower()
    if email not in _subscribers:
        _subscribers.append(email)
        logger.info(f"Added new subscriber: {email}")
    else:
        logger.info(f"Subscriber {email} already exists")
    return jsonify({"status":"success", "message":"Subscription successful"})

@app.route("/subscribers", methods=["GET"])
async def get_subscribers():
    return jsonify({"subscribers": _subscribers})

@app.route("/games/all", methods=["GET"])
@validate_querystring(GamesAllQuery)
async def get_all_games(query_args: GamesAllQuery):
    page = query_args.page
    limit = query_args.limit
    if page < 1 or limit < 1:
        return jsonify({"status":"error","message":"Page and limit must be positive integers"}), 400
    try:
        all_games_entities = await entity_service.get_items(
            token=cyoda_auth_service,
            entity_model="games_by_date",
            entity_version=ENTITY_VERSION,
        )
    except Exception as e:
        logger.exception(e)
        return jsonify({"status":"error","message":"Failed to retrieve games"}), 500
    all_games = []
    for entity in all_games_entities:
        games = entity.get("games", [])
        if isinstance(games, list):
            all_games.extend(games)
    total = len(all_games)
    start = (page - 1) * limit
    end = start + limit
    paged = all_games[start:end]
    return jsonify({
        "games": paged,
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total,
            "total_pages": (total + limit - 1) // limit if limit else 1
        }
    })

@app.route("/games/<string:date>", methods=["GET"])
async def get_games_by_date(date: str):
    try:
        datetime.datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        return jsonify({"status":"error","message":"Invalid date format, expected YYYY-MM-DD"}), 400
    try:
        entity = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model="games_by_date",
            entity_version=ENTITY_VERSION,
            technical_id=date
        )
    except Exception as e:
        logger.exception(e)
        return jsonify({"status":"error","message":"Failed to retrieve games for date"}), 500
    if not entity:
        return jsonify({"date": date, "games": []})
    games = entity.get("games", [])
    if not isinstance(games, list):
        games = []
    return jsonify({"date": date, "games": games})

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
