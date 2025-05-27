from dataclasses import dataclass
import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional

from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request, validate_querystring
import httpx

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

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

# In-memory "persistence"
_subscribers: Dict[str, Dict] = {}
_games_cache: List[Dict] = []
_entity_job: Dict[str, Dict] = {}

NBA_API_BASE = "https://www.balldontlie.io/api/v1"

async def fetch_nba_games() -> List[Dict]:
    today = datetime.utcnow().date().isoformat()
    url = f"{NBA_API_BASE}/games"
    params = {"dates[]": today, "per_page": 100}
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(url, params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            games = data.get("data", [])
            logger.info(f"Fetched {len(games)} games for {today}")
            return games
        except Exception as e:
            logger.exception(f"Failed to fetch NBA games: {e}")
            return []

async def send_email_mock(email: str, subject: str, content: str):
    logger.info(f"Sending email to {email} with subject '{subject}'")
    await asyncio.sleep(0.1)  # TODO: Replace with real email sending logic

async def process_entity(job_id: str):
    logger.info(f"Processing job {job_id}")
    try:
        games = await fetch_nba_games()
        stored_games = []
        for g in games:
            stored_games.append({
                "gameId": str(g["id"]),
                "date": g["date"][:10],
                "homeTeam": g["home_team"]["full_name"],
                "awayTeam": g["visitor_team"]["full_name"],
                "homeScore": g["home_team_score"],
                "awayScore": g["visitor_team_score"],
                "status": g["status"].lower(),
            })
        _games_cache.clear()
        _games_cache.extend(stored_games)
        logger.info(f"Stored {len(stored_games)} games")

        tasks = []
        for email, sub in _subscribers.items():
            pref_teams = sub.get("preferences", {}).get("favoriteTeams", [])
            relevant_games = [
                g for g in stored_games
                if not pref_teams or g["homeTeam"] in pref_teams or g["awayTeam"] in pref_teams
            ]
            if not relevant_games:
                continue
            content_lines = [
                f"{g['awayTeam']} @ {g['homeTeam']} | {g['awayScore']} - {g['homeScore']} | {g['status']}"
                for g in relevant_games
            ]
            content = "\n".join(content_lines)
            subject = f"NBA Daily Scores - {datetime.utcnow().date().isoformat()}"
            tasks.append(send_email_mock(email, subject, content))

        await asyncio.gather(*tasks)
        logger.info(f"Sent notifications to {len(tasks)} subscribers")
        _entity_job[job_id]["status"] = "completed"
    except Exception as e:
        _entity_job[job_id]["status"] = "failed"
        logger.exception(f"Job {job_id} failed: {e}")

@app.route("/subscribe", methods=["POST"])
# validation last for POST due to quart-schema defect
@validate_request(SubscribeRequest)
async def subscribe(data: SubscribeRequest):
    email = data.email
    prefs = {"favoriteTeams": data.favoriteTeams or []}
    _subscribers[email] = {"email": email, "preferences": prefs}
    logger.info(f"Subscribed {email} with {prefs}")
    return jsonify({"message": "Subscription successful", "subscriberId": email})

@app.route("/unsubscribe", methods=["POST"])
# validation last for POST due to quart-schema defect
@validate_request(UnsubscribeRequest)
async def unsubscribe(data: UnsubscribeRequest):
    email = data.email
    removed = _subscribers.pop(email, None)
    if removed:
        logger.info(f"Unsubscribed {email}")
        return jsonify({"message": "Unsubscribed successfully"})
    return jsonify({"message": "Email not found"}), 404

@app.route("/subscribers", methods=["GET"])
async def get_subscribers():
    return jsonify(list(_subscribers.values()))

@app.route("/fetch-games", methods=["POST"])
async def fetch_games():
    job_id = f"job_{datetime.utcnow().isoformat()}"
    _entity_job[job_id] = {"status": "processing", "requestedAt": datetime.utcnow().isoformat()}
    asyncio.create_task(process_entity(job_id))
    return jsonify({"message": "Games fetch started", "jobId": job_id})

# validation first for GET due to quart-schema defect
@validate_querystring(GamesQuery)
@app.route("/games", methods=["GET"])
async def get_games():
    date_filter = request.args.get("date")
    team_filter = request.args.get("team")
    results = _games_cache
    if date_filter:
        results = [g for g in results if g["date"] == date_filter]
    if team_filter:
        results = [g for g in results if team_filter in (g["homeTeam"], g["awayTeam"])]
    return jsonify(results)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    app.run(use_reloader=False, debug=True, host="0.0.0.0", port=8000, threaded=True)