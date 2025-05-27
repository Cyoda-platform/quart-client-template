from dataclasses import dataclass
import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional

from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request, validate_querystring
import httpx

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
    favoriteTeams: Optional[List[str]] = None

@dataclass
class UnsubscribeRequest:
    email: str

@dataclass
class GamesQuery:
    date: Optional[str] = None
    team: Optional[str] = None

_entity_job: Dict[str, Dict] = {}

NBA_API_BASE = "https://www.balldontlie.io/api/v1"

async def send_email_mock(email: str, subject: str, content: str):
    # Simulated email sending; replace with real implementation.
    logger.info(f"Sending email to {email} with subject '{subject}'")
    await asyncio.sleep(0.1)

async def process_games_fetch_job(entity: Dict) -> Dict:
    # This workflow fetches NBA games, adds them as 'games' entities, and notifies subscribers.
    logger.info("Starting games fetch job workflow")
    try:
        today = datetime.utcnow().date().isoformat()
        url = f"{NBA_API_BASE}/games"
        params = {"dates[]": today, "per_page": 100}
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            games = data.get("data", [])
            logger.info(f"Fetched {len(games)} games for {today}")

        # Add each fetched game as a separate entity in "games"
        for g in games:
            game_entity = {
                "gameId": str(g["id"]),
                "date": g["date"][:10],
                "homeTeam": g["home_team"]["full_name"],
                "awayTeam": g["visitor_team"]["full_name"],
                "homeScore": g["home_team_score"],
                "awayScore": g["visitor_team_score"],
                "status": g["status"].lower(),
            }
            try:
                await entity_service.add_item(
                    token=cyoda_auth_service,
                    entity_model="games",
                    entity_version=ENTITY_VERSION,
                    entity=game_entity,
                    workflow=process_games
                )
            except Exception as e:
                logger.exception(f"Failed to add game {game_entity.get('gameId')}: {e}")

        # Notify subscribers asynchronously
        try:
            subscribers = await entity_service.get_items(
                token=cyoda_auth_service,
                entity_model="subscribers",
                entity_version=ENTITY_VERSION
            )
        except Exception as e:
            logger.exception(f"Failed to get subscribers: {e}")
            subscribers = []

        stored_games = [{
            "gameId": str(g["id"]),
            "date": g["date"][:10],
            "homeTeam": g["home_team"]["full_name"],
            "awayTeam": g["visitor_team"]["full_name"],
            "homeScore": g["home_team_score"],
            "awayScore": g["visitor_team_score"],
            "status": g["status"].lower(),
        } for g in games]

        async def notify(sub: Dict):
            email = sub.get("email")
            if not email:
                return
            pref_teams = sub.get("preferences", {}).get("favoriteTeams", [])
            relevant_games = [
                g for g in stored_games
                if not pref_teams or g["homeTeam"] in pref_teams or g["awayTeam"] in pref_teams
            ]
            if not relevant_games:
                return
            content_lines = [
                f"{g['awayTeam']} @ {g['homeTeam']} | {g['awayScore']} - {g['homeScore']} | {g['status']}"
                for g in relevant_games
            ]
            content = "\n".join(content_lines)
            subject = f"NBA Daily Scores - {today}"
            try:
                await send_email_mock(email, subject, content)
            except Exception as e:
                logger.exception(f"Failed to send email to {email}: {e}")

        # Fire all notifications concurrently but do not raise on single failure
        await asyncio.gather(*(notify(sub) for sub in subscribers), return_exceptions=True)

        logger.info(f"Sent notifications to {len(subscribers)} subscribers")

    except Exception as e:
        logger.exception(f"Error in process_games_fetch_job workflow: {e}")

    return entity  # Return entity, could add status or timestamps here if desired

async def process_games(entity: Dict) -> Dict:
    # Enrich or normalize game entity data before persistence
    if "status" in entity and isinstance(entity["status"], str):
        entity["status"] = entity["status"].lower()
    # Additional enrichment could be added here
    return entity

async def process_subscribers(entity: Dict) -> Dict:
    # Send welcome email asynchronously after subscriber entity is persisted
    email = entity.get("email")
    if email:
        async def send_welcome():
            subject = "Welcome to NBA Scores!"
            content = f"Hi {email}, thanks for subscribing to NBA daily scores notifications!"
            try:
                await send_email_mock(email, subject, content)
            except Exception as e:
                logger.exception(f"Failed to send welcome email to {email}: {e}")
        asyncio.create_task(send_welcome())
    return entity

@app.route("/subscribe", methods=["POST"])
@validate_request(SubscribeRequest)
async def subscribe(data: SubscribeRequest):
    email = data.email
    prefs = {"favoriteTeams": data.favoriteTeams or []}
    entity = {
        "email": email,
        "preferences": prefs
    }
    try:
        id = await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model="subscribers",
            entity_version=ENTITY_VERSION,
            entity=entity,
            workflow=process_subscribers
        )
        return jsonify({"id": id})
    except Exception as e:
        logger.exception(e)
        return jsonify({"message": "Failed to subscribe"}), 500

@app.route("/unsubscribe", methods=["POST"])
@validate_request(UnsubscribeRequest)
async def unsubscribe(data: UnsubscribeRequest):
    email = data.email
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
            entity_model="subscribers",
            entity_version=ENTITY_VERSION,
            condition=condition
        )
        if not items:
            return jsonify({"message": "Email not found"}), 404
        item = items[0]
        tech_id = str(item.get("id") or item.get("technical_id") or item.get("email") or email)
        await entity_service.delete_item(
            token=cyoda_auth_service,
            entity_model="subscribers",
            entity_version=ENTITY_VERSION,
            technical_id=tech_id,
            meta={}
        )
        logger.info(f"Unsubscribed {email}")
        return jsonify({"message": "Unsubscribed successfully"})
    except Exception as e:
        logger.exception(e)
        return jsonify({"message": "Failed to unsubscribe"}), 500

@app.route("/subscribers", methods=["GET"])
async def get_subscribers():
    try:
        items = await entity_service.get_items(
            token=cyoda_auth_service,
            entity_model="subscribers",
            entity_version=ENTITY_VERSION
        )
        return jsonify(items)
    except Exception as e:
        logger.exception(e)
        return jsonify({"message": "Failed to fetch subscribers"}), 500

@app.route("/fetch-games", methods=["POST"])
async def fetch_games():
    # Add a new games_fetch_job entity to trigger the workflow
    job_entity = {
        "requestedAt": datetime.utcnow().isoformat()
    }
    try:
        job_id = await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model="games_fetch_job",
            entity_version=ENTITY_VERSION,
            entity=job_entity,
            workflow=process_games_fetch_job
        )
        return jsonify({"message": "Games fetch job started", "jobId": job_id})
    except Exception as e:
        logger.exception(e)
        return jsonify({"message": "Failed to start games fetch job"}), 500

@validate_querystring(GamesQuery)
@app.route("/games", methods=["GET"])
async def get_games():
    date_filter = request.args.get("date")
    team_filter = request.args.get("team")
    try:
        games = await entity_service.get_items(
            token=cyoda_auth_service,
            entity_model="games",
            entity_version=ENTITY_VERSION
        )
        results = games
        if date_filter:
            results = [g for g in results if g.get("date") == date_filter]
        if team_filter:
            results = [g for g in results if team_filter in (g.get("homeTeam"), g.get("awayTeam"))]
        return jsonify(results)
    except Exception as e:
        logger.exception(e)
        return jsonify({"message": "Failed to fetch games"}), 500

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    app.run(use_reloader=False, debug=True, host="0.0.0.0", port=8000, threaded=True)