from dataclasses import dataclass
from typing import Optional
import asyncio
import datetime
import logging
from typing import Dict, List

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# In-memory "database" mocks
subscribers: set = set()
games_storage: Dict[str, List[dict]] = {}  # key = date str "YYYY-MM-DD", value = list of games

# Entity job tracking for async processing
entity_job: Dict[str, dict] = {}

API_KEY = "test"
API_URL_TEMPLATE = "https://api.sportsdata.io/v3/nba/scores/json/ScoresBasicFinal/{date}?key=" + API_KEY

@dataclass
class SubscribeData:
    email: str

@dataclass
class FetchScoresData:
    date: str

async def fetch_nba_scores(date: str) -> List[dict]:
    url = API_URL_TEMPLATE.format(date=date)
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.get(url)
            resp.raise_for_status()
            data = resp.json()
            # TODO: Confirm exact data shape returned by real API, here we assume it's a list of game dicts
            return data
        except httpx.HTTPError as e:
            logger.exception(f"Failed to fetch NBA scores for {date}: {e}")
            return []

async def send_email_notification(to_emails: List[str], date: str, games: List[dict]) -> None:
    # TODO: Implement real email sending logic
    # For prototype, we just log the notification
    logger.info(f"Sending NBA scores notification for {date} to {len(to_emails)} subscribers")
    summary = f"NBA Scores for {date}:\n"
    for g in games:
        # Assuming keys 'HomeTeam', 'AwayTeam', 'HomeTeamScore', 'AwayTeamScore', 'Status' exist in game dict
        summary += f"{g.get('AwayTeam')} at {g.get('HomeTeam')}: {g.get('AwayTeamScore')} - {g.get('HomeTeamScore')} ({g.get('Status')})\n"
    # Log summary instead of sending email
    logger.info(f"Email content:\n{summary}")

async def process_fetch_store_notify(job_id: str, date: str):
    try:
        entity_job[job_id]["status"] = "fetching"
        games = await fetch_nba_scores(date)
        entity_job[job_id]["status"] = "storing"
        # Store games in local cache
        games_storage[date] = games
        entity_job[job_id]["status"] = "notifying"
        if subscribers:
            await send_email_notification(list(subscribers), date, games)
        entity_job[job_id]["status"] = "completed"
        logger.info(f"Completed processing fetch-store-notify job {job_id} for date {date}")
    except Exception as e:
        logger.exception(f"Error processing fetch-store-notify job {job_id} for date {date}: {e}")
        entity_job[job_id]["status"] = "failed"

# POST - validate_request placed after route decorator (last) - per library issue workaround
@app.route("/subscribe", methods=["POST"])
@validate_request(SubscribeData)
async def subscribe(data: SubscribeData):
    email = data.email
    if not email or not isinstance(email, str):
        return jsonify({"error": "Invalid email"}), 400
    if email in subscribers:
        return jsonify({"message": "Email already subscribed", "email": email}), 200
    subscribers.add(email)
    logger.info(f"New subscription: {email}")
    return jsonify({"message": "Subscription successful", "email": email}), 201

# GET - no validation needed for this endpoint as per instruction
@app.route("/subscribers", methods=["GET"])
async def get_subscribers():
    return jsonify({"subscribers": list(subscribers)}), 200

# GET - no request body or query params validation (optional pagination via query params)
@app.route("/games/all", methods=["GET"])
async def get_all_games():
    try:
        page = int(request.args.get("page", 1))
        limit = int(request.args.get("limit", 20))
    except ValueError:
        return jsonify({"error": "Invalid pagination parameters"}), 400
    all_games = []
    for games_list in games_storage.values():
        all_games.extend(games_list)
    start = (page - 1) * limit
    end = start + limit
    paged_games = all_games[start:end]
    return jsonify({
        "games": paged_games,
        "page": page,
        "limit": limit,
        "total": len(all_games),
    }), 200

# GET - no validation needed for path param, but we validate date format inside
@app.route("/games/<date>", methods=["GET"])
async def get_games_by_date(date: str):
    try:
        datetime.datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        return jsonify({"error": "Invalid date format, use YYYY-MM-DD"}), 400
    games = games_storage.get(date, [])
    return jsonify({"date": date, "games": games}), 200

# POST - validate_request placed after route decorator (last) - per library issue workaround
@app.route("/fetch-scores", methods=["POST"])
@validate_request(FetchScoresData)
async def fetch_scores(data: FetchScoresData):
    date = data.date
    # Validate date format YYYY-MM-DD just in case
    try:
        datetime.datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        return jsonify({"error": "Invalid date format, use YYYY-MM-DD"}), 400

    job_id = f"job_{datetime.datetime.utcnow().isoformat()}"
    entity_job[job_id] = {
        "status": "queued",
        "requestedAt": datetime.datetime.utcnow().isoformat(),
    }
    asyncio.create_task(process_fetch_store_notify(job_id, date))

    return jsonify({"message": "Scores fetch started", "job_id": job_id}), 202

if __name__ == '__main__':
    import sys

    logging.basicConfig(stream=sys.stdout, level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s : %(message)s")

    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
```