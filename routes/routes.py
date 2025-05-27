from dataclasses import dataclass
from typing import Optional, List
import asyncio
import logging
from datetime import datetime, timezone

import httpx
from quart import Quart, request, jsonify
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

@dataclass
class SubscribeRequest:
    email: str

@dataclass
class FetchScoresRequest:
    date: Optional[str] = None

@dataclass
class PageParams:
    page: Optional[int] = 1
    limit: Optional[int] = 20

ENTITY_NAME = "subscriber"
GAMES_ENTITY_NAME = "game"

async def process_subscriber(entity_data: dict) -> dict:
    if "created_at" not in entity_data:
        entity_data["created_at"] = datetime.now(timezone.utc).isoformat()
    return entity_data

async def process_game(entity_data: dict) -> dict:
    if "processed_at" not in entity_data:
        entity_data["processed_at"] = datetime.now(timezone.utc).isoformat()

    date = entity_data.get("date")
    games = entity_data.get("games", [])

    if not date or not isinstance(games, list):
        logger.warning("process_game: missing or invalid 'date' or 'games' in entity_data")
        return entity_data

    try:
        subscribers = await entity_service.get_items(
            token=cyoda_auth_service,
            entity_model=ENTITY_NAME,
            entity_version=ENTITY_VERSION,
        )
        emails = [sub.get("email") for sub in subscribers if "email" in sub]
    except Exception as e:
        logger.exception(f"process_game: Failed to fetch subscribers: {e}")
        emails = []

    if emails:
        subject = f"NBA Scores for {date}"
        content = format_email_content(date, games)
        asyncio.create_task(send_email(emails, subject, content))
    else:
        logger.info("process_game: No subscribers found to notify")

    return entity_data

async def add_subscriber(email: str) -> str:
    data = {"email": email}
    try:
        id = await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model=ENTITY_NAME,
            entity_version=ENTITY_VERSION,
            entity=data
        )
        return id
    except Exception as e:
        logger.exception(f"Failed to add subscriber {email}: {e}")
        raise

async def get_all_subscribers() -> List[str]:
    try:
        items = await entity_service.get_items(
            token=cyoda_auth_service,
            entity_model=ENTITY_NAME,
            entity_version=ENTITY_VERSION,
        )
        emails = [item.get("email") for item in items if "email" in item]
        return emails
    except Exception as e:
        logger.exception(f"Failed to get subscribers: {e}")
        return []

async def get_games_by_date(date: str) -> List[dict]:
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
            entity_model=GAMES_ENTITY_NAME,
            entity_version=ENTITY_VERSION,
            condition=condition
        )
        games_list = []
        for item in items:
            games = item.get("games", [])
            if isinstance(games, list):
                games_list.extend(games)
        return games_list
    except Exception as e:
        logger.exception(f"Failed to get games for date {date}: {e}")
        return []

async def get_all_games() -> List[dict]:
    try:
        items = await entity_service.get_items(
            token=cyoda_auth_service,
            entity_model=GAMES_ENTITY_NAME,
            entity_version=ENTITY_VERSION,
        )
        all_games = []
        for item in items:
            games = item.get("games", [])
            if isinstance(games, list):
                all_games.extend(games)
        return all_games
    except Exception as e:
        logger.exception(f"Failed to get all games: {e}")
        return []

API_KEY = "test"
API_ENDPOINT_TEMPLATE = "https://api.sportsdata.io/v3/nba/scores/json/ScoresBasicFinal/{date}?key={key}"

async def send_email(to_emails: List[str], subject: str, content: str):
    logger.info(f"Sending Email to {len(to_emails)} subscribers with subject: {subject}")
    await asyncio.sleep(0.1)
    logger.info("Email sent.")

async def fetch_scores_for_date(date: str) -> List[dict]:
    url = API_ENDPOINT_TEMPLATE.format(date=date, key=API_KEY)
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, timeout=20)
            response.raise_for_status()
            data = response.json()
            if not isinstance(data, list):
                logger.warning(f"Unexpected data format from external API for {date}: {data}")
                return []
            logger.info(f"Fetched {len(data)} games for {date} from external API.")
            return data
        except httpx.HTTPError as e:
            logger.exception(f"HTTP error while fetching scores for {date}: {e}")
            return []
        except Exception as e:
            logger.exception(f"Unexpected error while fetching scores for {date}: {e}")
            return []

def format_email_content(date: str, games: List[dict]) -> str:
    if not games:
        return f"No NBA games found for {date}."
    lines = [f"NBA Scores for {date}:
"]
    for g in games:
        home_team = g.get("HomeTeam", "N/A")
        away_team = g.get("AwayTeam", "N/A")
        home_score = g.get("HomeTeamScore", "N/A")
        away_score = g.get("AwayTeamScore", "N/A")
        lines.append(f"{away_team} @ {home_team} 1 : {home_score}")
    return "\n".join(lines)

@app.route("/subscribe", methods=["POST"])
@validate_request(SubscribeRequest)
async def subscribe(data: SubscribeRequest):
    email = data.email.strip().lower()
    if not email or "@" not in email:
        return jsonify({"error": "Invalid email address"}), 400
    try:
        await add_subscriber(email)
        logger.info(f"New subscription added: {email}")
        return jsonify({"message": "Subscription successful", "email": email})
    except Exception:
        return jsonify({"error": "Failed to add subscription"}), 500

@app.route("/subscribers", methods=["GET"])
async def get_subscribers():
    subs = await get_all_subscribers()
    return jsonify({"subscribers": subs})

@validate_querystring(PageParams)
@app.route("/games/all", methods=["GET"])
async def get_all_games_route():
    try:
        page = int(request.args.get("page", 1))
        limit = int(request.args.get("limit", 20))
        if page < 1 or limit < 1:
            raise ValueError
    except ValueError:
        return jsonify({"error": "Invalid pagination parameters"}), 400

    all_games_list = await get_all_games()
    total = len(all_games_list)
    start = (page - 1) * limit
    end = start + limit
    paged_games = all_games_list[start:end]

    return jsonify({
        "games": paged_games,
        "page": page,
        "limit": limit,
        "total": total
    })

@app.route("/games/<string:date>", methods=["GET"])
async def get_games_by_date_route(date):
    try:
        datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        return jsonify({"error": "Invalid date format, expected YYYY-MM-DD"}), 400

    games = await get_games_by_date(date)
    return jsonify({"date": date, "games": games})

@app.route("/fetch-scores", methods=["POST"])
@validate_request(FetchScoresRequest)
async def fetch_scores(data: FetchScoresRequest):
    date = data.date
    if date:
        try:
            datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            return jsonify({"error": "Invalid date format, expected YYYY-MM-DD"}), 400
    else:
        date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    games = await fetch_scores_for_date(date)
    if not games:
        return jsonify({"message": "No games fetched or error occurred", "date": date, "games_fetched": 0})

    data_to_store = {"date": date, "games": games}
    try:
        await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model=GAMES_ENTITY_NAME,
            entity_version=ENTITY_VERSION,
            entity=data_to_store
        )
        return jsonify({"message": "Scores fetched, stored, and notifications scheduled", "date": date, "games_fetched": len(games)})
    except Exception as e:
        logger.exception(f"Failed to store games for {date}: {e}")
        return jsonify({"error": "Failed to store fetched games"}), 500

if __name__ == '__main__':
    import sys
    logging.basicConfig(
        stream=sys.stdout,
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
