from dataclasses import dataclass
import asyncio
import datetime
import logging
from typing import Dict, List, Optional

import httpx
from quart import Quart, jsonify, request
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

@dataclass
class SubscribeRequest:
    email: str
    notificationType: str

@dataclass
class FetchRequest:
    date: str

@dataclass
class GamesQuery:
    date: Optional[str] = None
    team: Optional[str] = None
    offset: int = 0
    limit: int = 10

entity_name = "subscriber"
game_entity_name = "game"

API_KEY = "test"
NBA_API_URL = "https://api.sportsdata.io/v3/nba/scores/json/ScoresBasicFinal/{date}?key={key}"
SCHEDULER_TIME_UTC = "18:00"

# In-memory cache to track notification sending per date (thread-safe for this single-process app)
_notification_sent_for_date = set()
_notification_lock = asyncio.Lock()


async def process_subscriber(entity: Dict) -> None:
    """
    Workflow function applied to subscriber entity before persistence.
    Normalize email to lowercase.
    """
    email = entity.get("email")
    if email:
        entity["email"] = email.strip().lower()


async def process_game(entity: Dict) -> None:
    """
    Workflow function applied to game entity before persistence.
    Normalize status field and send notifications once per date.
    """
    status = entity.get("Status")
    if status:
        entity["Status"] = status.upper()

    date_str = entity.get("Day")
    if not date_str:
        return

    async with _notification_lock:
        if date_str in _notification_sent_for_date:
            return
        _notification_sent_for_date.add(date_str)

    # Fire-and-forget notification sending
    asyncio.create_task(_send_notifications_for_date(date_str))


async def _send_notifications_for_date(date_str: str):
    try:
        condition = {
            "cyoda": {
                "type": "group",
                "operator": "AND",
                "conditions": [
                    {
                        "jsonPath": "$.Day",
                        "operatorType": "EQUALS",
                        "value": date_str,
                        "type": "simple"
                    }
                ]
            }
        }
        games = await entity_service.get_items_by_condition(
            token=cyoda_auth_service,
            entity_model=game_entity_name,
            entity_version=ENTITY_VERSION,
            condition=condition
        )
        if not games:
            logger.info(f"No games found for date {date_str} to notify.")
            return

        subs = await entity_service.get_items(
            token=cyoda_auth_service,
            entity_model=entity_name,
            entity_version=ENTITY_VERSION
        )
        if not subs:
            logger.info("No subscribers to notify.")
            return

        for sub in subs:
            email = sub.get("email")
            nt = sub.get("notificationType", "summary")
            if not email:
                continue
            content = _build_email_content(date_str, games, nt)
            # TODO: Implement real email sending here
            logger.info(f"Sending {nt} email to {email} for {date_str}")
            await asyncio.sleep(0.1)  # simulate sending email

    except Exception:
        logger.exception("Failed to send notifications")


def _build_email_content(date_str: str, games: List[Dict], notification_type: str) -> str:
    if notification_type == "summary":
        total_games = len(games)
        total_points = sum(
            (g.get("HomeTeamScore", 0) or 0) + (g.get("AwayTeamScore", 0) or 0) for g in games
        )
        return f"""
        <html>
        <body>
            <h2>NBA Summary for {date_str}</h2>
            <p>Total games played: {total_games}</p>
            <p>Total points scored: {total_points}</p>
        </body>
        </html>
        """
    rows = ""
    for g in games:
        rows += f"<tr><td>{g.get('HomeTeam')}</td><td>{g.get('HomeTeamScore')}</td>" \
                f"<td>vs</td><td>{g.get('AwayTeam')}</td><td>{g.get('AwayTeamScore')}</td>" \
                f"<td>{g.get('Status')}</td></tr>"
    return f"""
        <html>
        <body>
            <h2>NBA Full Details for {date_str}</h2>
            <table border="1" cellpadding="5" cellspacing="0">
                <tr><th>Home Team</th><th>Score</th><th></th><th>Away Team</th><th>Score</th><th>Status</th></tr>
                {rows}
            </table>
        </body>
        </html>
    """

@app.route("/subscribe", methods=["POST"])
@validate_request(SubscribeRequest)
async def subscribe(data: SubscribeRequest):
    try:
        email = data.email
        notification_type = data.notificationType
        if notification_type not in ("summary", "full"):
            return jsonify({"error": "Invalid notificationType"}), 400

        subscriber_data = {"email": email, "notificationType": notification_type}

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
        existing_subs = await entity_service.get_items_by_condition(
            token=cyoda_auth_service,
            entity_model=entity_name,
            entity_version=ENTITY_VERSION,
            condition=condition
        )
        if existing_subs:
            existing_id = existing_subs[0].get("technical_id") or existing_subs[0].get("id") or existing_subs[0].get("email")
            await entity_service.update_item(
                token=cyoda_auth_service,
                entity_model=entity_name,
                entity_version=ENTITY_VERSION,
                entity=subscriber_data,
                technical_id=str(existing_id),
                meta={}
            )
        else:
            await entity_service.add_item(
                token=cyoda_auth_service,
                entity_model=entity_name,
                entity_version=ENTITY_VERSION,
                entity=subscriber_data
            )

        logger.info(f"New subscription: {email} with preference {notification_type}")
        return jsonify({
            "message": "Subscription successful",
            "email": email,
            "notificationType": notification_type
        })
    except Exception:
        logger.exception("Failed to subscribe")
        return jsonify({"error": "Failed to subscribe"}), 500

@app.route("/subscribers", methods=["GET"])
async def get_subscribers():
    try:
        subs = await entity_service.get_items(
            token=cyoda_auth_service,
            entity_model=entity_name,
            entity_version=ENTITY_VERSION
        )
        result = []
        for sub in subs:
            email = sub.get("email")
            notification_type = sub.get("notificationType")
            if email and notification_type:
                result.append({"email": email, "notificationType": notification_type})
        return jsonify(result)
    except Exception:
        logger.exception("Failed to retrieve subscribers")
        return jsonify({"error": "Failed to retrieve subscribers"}), 500

@app.route("/games/fetch", methods=["POST"])
@validate_request(FetchRequest)
async def fetch_and_store_games(data: FetchRequest):
    try:
        date_str = data.date
        try:
            datetime.datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            return jsonify({"error": "Date must be in YYYY-MM-DD format"}), 400

        asyncio.create_task(_fetch_process(date_str))
        return jsonify({
            "message": "Scores fetch started",
            "date": date_str
        })
    except Exception:
        logger.exception("Failed to trigger fetch")
        return jsonify({"error": "Failed to trigger fetch"}), 500

async def _fetch_process(date_str: str):
    try:
        url = NBA_API_URL.format(date=date_str, key=API_KEY)
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            games = resp.json()
            logger.info(f"Fetched {len(games)} games for {date_str}")

        condition = {
            "cyoda": {
                "type": "group",
                "operator": "AND",
                "conditions": [
                    {
                        "jsonPath": "$.Day",
                        "operatorType": "EQUALS",
                        "value": date_str,
                        "type": "simple"
                    }
                ]
            }
        }
        old_games = await entity_service.get_items_by_condition(
            token=cyoda_auth_service,
            entity_model=game_entity_name,
            entity_version=ENTITY_VERSION,
            condition=condition
        )
        for old_game in old_games:
            old_id = old_game.get("technical_id") or old_game.get("id")
            if old_id:
                await entity_service.delete_item(
                    token=cyoda_auth_service,
                    entity_model=game_entity_name,
                    entity_version=ENTITY_VERSION,
                    technical_id=str(old_id),
                    meta={}
                )

        for game in games:
            await entity_service.add_item(
                token=cyoda_auth_service,
                entity_model=game_entity_name,
                entity_version=ENTITY_VERSION,
                entity=game
            )
    except Exception:
        logger.exception("Failed during fetch process")

@validate_querystring(GamesQuery)
@app.route("/games/all", methods=["GET"])
async def get_all_games():
    try:
        date_filter = request.args.get("date")
        team_filter = request.args.get("team")
        offset = request.args.get("offset", default=0, type=int)
        limit = request.args.get("limit", default=10, type=int)

        all_games = []
        if date_filter:
            condition = {
                "cyoda": {
                    "type": "group",
                    "operator": "AND",
                    "conditions": [
                        {
                            "jsonPath": "$.Day",
                            "operatorType": "EQUALS",
                            "value": date_filter,
                            "type": "simple"
                        }
                    ]
                }
            }
            filtered_games = await entity_service.get_items_by_condition(
                token=cyoda_auth_service,
                entity_model=game_entity_name,
                entity_version=ENTITY_VERSION,
                condition=condition
            )
            all_games.extend(filtered_games)
        else:
            all_games = await entity_service.get_items(
                token=cyoda_auth_service,
                entity_model=game_entity_name,
                entity_version=ENTITY_VERSION
            )

        if team_filter:
            tf = team_filter.lower()
            all_games = [
                g for g in all_games
                if tf in (g.get("HomeTeam") or "").lower() or tf in (g.get("AwayTeam") or "").lower()
            ]

        total = len(all_games)
        paged = all_games[offset: offset + limit]

        def norm(g: Dict) -> Dict:
            return {
                "gameId": g.get("GameID"),
                "date": g.get("Day"),
                "homeTeam": g.get("HomeTeam"),
                "awayTeam": g.get("AwayTeam"),
                "homeScore": g.get("HomeTeamScore"),
                "awayScore": g.get("AwayTeamScore"),
                "status": g.get("Status"),
            }

        return jsonify({
            "games": [norm(g) for g in paged],
            "pagination": {"offset": offset, "limit": limit, "total": total}
        })
    except Exception:
        logger.exception("Failed to retrieve games")
        return jsonify({"error": "Failed to retrieve games"}), 500

@app.route("/games/<date>", methods=["GET"])
async def get_games_by_date(date: str):
    try:
        try:
            datetime.datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            return jsonify({"error": "Date must be in YYYY-MM-DD format"}), 400

        condition = {
            "cyoda": {
                "type": "group",
                "operator": "AND",
                "conditions": [
                    {
                        "jsonPath": "$.Day",
                        "operatorType": "EQUALS",
                        "value": date,
                        "type": "simple"
                    }
                ]
            }
        }
        games = await entity_service.get_items_by_condition(
            token=cyoda_auth_service,
            entity_model=game_entity_name,
            entity_version=ENTITY_VERSION,
            condition=condition
        )

        def norm(g: Dict) -> Dict:
            return {
                "gameId": g.get("GameID"),
                "date": g.get("Day"),
                "homeTeam": g.get("HomeTeam"),
                "awayTeam": g.get("AwayTeam"),
                "homeScore": g.get("HomeTeamScore"),
                "awayScore": g.get("AwayTeamScore"),
                "status": g.get("Status"),
            }

        return jsonify({
            "games": [norm(g) for g in games],
            "pagination": {"offset": 0, "limit": len(games), "total": len(games)}
        })
    except Exception:
        logger.exception("Failed to retrieve games")
        return jsonify({"error": "Failed to retrieve games"}), 500

async def _scheduler_loop():
    while True:
        now = datetime.datetime.utcnow()
        target = datetime.datetime.strptime(SCHEDULER_TIME_UTC, "%H:%M").time()
        next_run = datetime.datetime.combine(now.date(), target)
        if now.time() >= target:
            next_run += datetime.timedelta(days=1)
        sleep_seconds = (next_run - now).total_seconds()
        if sleep_seconds > 0:
            await asyncio.sleep(sleep_seconds)
        today_str = datetime.datetime.utcnow().strftime("%Y-%m-%d")
        logger.info(f"Scheduler triggering fetch for {today_str}")
        asyncio.create_task(_fetch_process(today_str))

@app.before_serving
async def startup():
    app.add_background_task(_scheduler_loop)

if __name__ == '__main__':
    import sys
    logging.basicConfig(
        level=logging.INFO,
        stream=sys.stdout,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s"
    )
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
