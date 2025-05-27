from dataclasses import dataclass
import asyncio
import logging
from datetime import datetime

from quart import Blueprint, request, jsonify
from quart_schema import validate_request, validate_querystring

import httpx

from app_init.app_init import BeanFactory
from common.config.config import ENTITY_VERSION

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

factory = BeanFactory(config={'CHAT_REPOSITORY': 'cyoda'})
entity_service = factory.get_services()['entity_service']
cyoda_auth_service = factory.get_services()["cyoda_auth_service"]

routes_bp = Blueprint('routes', __name__)

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
entity_name_nba_scores_raw = "nba_scores_raw"

NBA_API_KEY = "test"
NBA_API_URL = "https://api.sportsdata.io/v3/nba/scores/json/ScoresBasicFinal/{date}?key=" + NBA_API_KEY


async def send_email(to_emails: list, subject: str, body: str):
    # Mock sending email
    await asyncio.sleep(0.1)
    logger.info(f"Email sent to {len(to_emails)} recipients\nSubject: {subject}\n{body}")


def build_email_body(date: str, games: list) -> str:
    if not games:
        return f"No NBA games found for {date}."
    lines = [f"NBA Scores for {date}:\n"]
    for g in games:
        home = g.get("HomeTeam", "Home")
        away = g.get("AwayTeam", "Away")
        home_score = g.get("HomeTeamScore", "N/A")
        away_score = g.get("AwayTeamScore", "N/A")
        lines.append(f"{away} @ {home} 	6 {away_score}:{home_score}")
    return "\n".join(lines)


async def list_subscribers_emails() -> list:
    try:
        items = await entity_service.get_items(
            token=cyoda_auth_service,
            entity_model=entity_name_subscriber,
            entity_version=ENTITY_VERSION,
        )
        return [item["email"] for item in items if "email" in item]
    except Exception:
        logger.exception("Failed to list subscribers")
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
    except Exception:
        logger.exception("Failed to check subscriber existence")
        return False


async def process_subscriber(entity: dict) -> dict:
    """
    Workflow called before persisting new subscriber entity.
    Sends a welcome email and adds subscribed_at timestamp.
    """
    entity['subscribed_at'] = datetime.utcnow().isoformat()

    async def _send_welcome():
        try:
            await send_email(
                [entity['email']],
                "Welcome to NBA Scores Notification",
                "Thank you for subscribing to NBA scores notifications!"
            )
        except Exception:
            logger.exception("Failed to send welcome email")

    asyncio.create_task(_send_welcome())
    return entity


async def process_game(entity: dict) -> dict:
    """
    Workflow called before persisting a new game entity.
    Fetches NBA scores, enriches the entity with games data,
    sends notifications to all subscribers,
    and adds raw scores as supplementary entities.
    """
    date = entity.get("date")
    if not date:
        logger.warning("Game entity missing 'date' field")
        return entity

    url = NBA_API_URL.format(date=date)
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            scores = resp.json()
    except Exception:
        logger.exception(f"Failed to fetch NBA scores for {date}")
        scores = []

    entity["games"] = scores

    try:
        await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model=entity_name_nba_scores_raw,
            entity_version=ENTITY_VERSION,
            entity={
                "date": date,
                "raw_data": scores,
            },
            workflow=None
        )
    except Exception:
        logger.exception("Failed to add raw NBA scores entity")

    async def _notify_subscribers():
        try:
            subscribers = await list_subscribers_emails()
            if not subscribers:
                logger.info("No subscribers to notify")
                return
            subject = f"NBA Scores for {date}"
            body = build_email_body(date, scores)
            await send_email(subscribers, subject, body)
            logger.info(f"Notified {len(subscribers)} subscribers")
        except Exception:
            logger.exception("Failed to send notification emails")

    asyncio.create_task(_notify_subscribers())

    return entity


@routes_bp.route("/subscribe", methods=["POST"])
@validate_request(Subscriber)
async def subscribe(data: Subscriber):
    exists = await check_subscriber_exists(data.email)
    if exists:
        return jsonify({"message": "Email already subscribed", "email": data.email}), 409

    try:
        await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model=entity_name_subscriber,
            entity_version=ENTITY_VERSION,
            entity={"email": data.email}
        )
    except Exception:
        logger.exception("Failed to add subscriber entity")
        return jsonify({"message": "Failed to add subscriber"}), 500

    return jsonify({"message": "Subscription successful", "email": data.email}), 201


@routes_bp.route("/subscribers", methods=["GET"])
async def get_subscribers():
    emails = await list_subscribers_emails()
    return jsonify({"subscribers": emails})


@routes_bp.route("/fetch-scores", methods=["POST"])
@validate_request(FetchScores)
async def fetch_scores(data: FetchScores):
    try:
        datetime.strptime(data.date, "%Y-%m-%d")
    except ValueError:
        return jsonify({"message": "Invalid date format, expected YYYY-MM-DD"}), 400

    try:
        await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model=entity_name_game,
            entity_version=ENTITY_VERSION,
            entity={"date": data.date}
        )
    except Exception:
        logger.exception("Failed to add game entity")
        return jsonify({"message": "Failed to start score fetching"}), 500

    return jsonify({"message": f"Scores fetch started for {data.date}"}), 202


@routes_bp.route("/games/all", methods=["GET"])
@validate_querystring(GamesQuery)
async def get_all_games():
    page = request.args.get("page", default=1, type=int)
    limit = request.args.get("limit", default=50, type=int)
    if page < 1 or limit < 1:
        return jsonify({"message": "Page and limit must be positive integers"}), 400

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
        total = len(all_games)
        start = (page - 1) * limit
        end = start + limit
        paged_games = all_games[start:end]
    except Exception:
        logger.exception("Failed to retrieve games")
        return jsonify({"message": "Failed to retrieve games"}), 500

    return jsonify({
        "games": paged_games,
        "page": page,
        "limit": limit,
        "total": total
    })


@routes_bp.route("/games/<date>", methods=["GET"])
async def get_games_by_date(date):
    try:
        datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        return jsonify({"message": "Invalid date format, expected YYYY-MM-DD"}), 400

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
            return jsonify({"date": date, "games": []})
        games = items[0].get("games", [])
    except Exception:
        logger.exception(f"Failed to retrieve games for {date}")
        return jsonify({"message": "Failed to retrieve games"}), 500

    return jsonify({"date": date, "games": games})