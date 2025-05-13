import asyncio
import datetime
import logging
from dataclasses import dataclass
from typing import List, Dict

from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request, validate_querystring
import httpx

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# Workaround: quart-schema validate issue; for GET validation first, for POST last

@dataclass
class SubscribeRequest:
    email: str

@dataclass
class GamesQuery:
    page: int
    limit: int

# In-memory storage mocks
_subscribers: List[str] = []
_games_storage: Dict[str, List[Dict]] = {}
entity_job = {}

NBA_API_KEY = "test"
NBA_API_URL_TEMPLATE = "https://api.sportsdata.io/v3/nba/scores/json/ScoresBasicFinal/{date}?key=" + NBA_API_KEY

async def fetch_nba_scores_for_date(date_str: str) -> List[Dict]:
    url = NBA_API_URL_TEMPLATE.format(date=date_str)
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, timeout=20.0)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.exception(f"HTTP error while fetching NBA scores for {date_str}: {e}")
            return []
        except Exception as e:
            logger.exception(f"Unexpected error while fetching NBA scores for {date_str}: {e}")
            return []

async def send_email_notifications(date_str: str):
    games = _games_storage.get(date_str, [])
    summary_lines = []
    for game in games:
        summary_lines.append(
            f"{game.get('away_team')} at {game.get('home_team')} - {game.get('away_score')}:{game.get('home_score')} ({game.get('status')})"
        )
    summary = "\n".join(summary_lines) if summary_lines else "No games for this date."
    for email in _subscribers:
        logger.info(f"Sending email to {email}:\nNBA Scores for {date_str}:\n{summary}")

async def process_fetch_scores(job_id: str, date_str: str):
    try:
        entity_job[job_id]["status"] = "fetching"
        nba_data = await fetch_nba_scores_for_date(date_str)
        entity_job[job_id]["status"] = "storing"
        stored_games = []
        for game in nba_data:
            stored_game = {
                "date": game.get("Day", date_str),
                "home_team": game.get("HomeTeam", game.get("HomeTeamName", "Unknown")),
                "away_team": game.get("AwayTeam", game.get("AwayTeamName", "Unknown")),
                "home_score": game.get("HomeTeamScore", -1),
                "away_score": game.get("AwayTeamScore", -1),
                "status": game.get("Status", "unknown"),
            }
            stored_games.append(stored_game)
        _games_storage[date_str] = stored_games
        entity_job[job_id]["status"] = "notifying"
        await send_email_notifications(date_str)
        entity_job[job_id]["status"] = "completed"
    except Exception as e:
        logger.exception(f"Error processing fetch scores job {job_id}: {e}")
        entity_job[job_id]["status"] = "failed"

@app.route("/fetch-scores", methods=["POST"])
async def fetch_scores():
    date_str = datetime.datetime.utcnow().date().isoformat()
    job_id = f"fetch-{date_str}"
    if job_id in entity_job and entity_job[job_id]["status"] in ["processing", "fetching", "storing", "notifying"]:
        return jsonify({"status": "processing", "message": "Fetch already in progress for today."})
    entity_job[job_id] = {"status": "processing", "requestedAt": datetime.datetime.utcnow().isoformat()}
    asyncio.create_task(process_fetch_scores(job_id, date_str))
    return jsonify({"status": "accepted", "message": f"Fetching NBA scores for {date_str} started."})

@app.route("/subscribe", methods=["POST"])
@validate_request(SubscribeRequest)
async def subscribe(data: SubscribeRequest):
    email = data.email.strip().lower()
    if not email:
        return jsonify({"status": "error", "message": "Email is required"}), 400
    if email in _subscribers:
        return jsonify({"status": "success", "message": f"Already subscribed: {email}"})
    _subscribers.append(email)
    logger.info(f"New subscriber added: {email}")
    return jsonify({"status": "success", "message": f"Subscription successful for {email}"})

@validate_querystring(GamesQuery)
@app.route("/games/all", methods=["GET"])
async def get_all_games():
    args = GamesQuery(**{k: int(request.args.get(k)) for k in ("page", "limit")})
    page = args.page
    limit = args.limit
    all_games = []
    for games in _games_storage.values():
        all_games.extend(games)
    start = (page - 1) * limit
    end = start + limit
    paged_games = all_games[start:end]
    return jsonify({"games": paged_games})

@app.route("/subscribers", methods=["GET"])
async def get_subscribers():
    return jsonify({"subscribers": _subscribers})

@app.route("/games/<date_str>", methods=["GET"])
async def get_games_by_date(date_str: str):
    games = _games_storage.get(date_str, [])
    return jsonify({"date": date_str, "games": games})

if __name__ == "__main__":
    import sys
    logging.basicConfig(stream=sys.stdout, level=logging.INFO)
    app.run(use_reloader=False, debug=True, host="0.0.0.0", port=8000, threaded=True)