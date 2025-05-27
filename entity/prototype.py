import asyncio
import logging
from datetime import datetime
from typing import List, Dict, Optional

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request, validate_querystring
from dataclasses import dataclass

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# In-memory caches simulating persistence
_subscribers: List[str] = []
_games_by_date: Dict[str, List[Dict]] = {}
_entity_jobs: Dict[str, Dict] = {}

API_KEY = "test"
NBA_API_URL = "https://api.sportsdata.io/v3/nba/scores/json/ScoresBasicFinal/{date}?key=" + API_KEY

@dataclass
class SubscriptionRequest:
    email: str

@dataclass
class FetchScoresRequest:
    date: str

@dataclass
class GamesAllQuery:
    page: int = 1
    pageSize: int = 20
    startDate: Optional[str] = None
    endDate: Optional[str] = None

# Workaround: place validation first for GET and last for POST due to quart-schema issue

@app.route("/subscribe", methods=["POST"])
@validate_request(SubscriptionRequest)
async def subscribe(data: SubscriptionRequest):
    email = data.email
    if email not in _subscribers:
        _subscribers.append(email)
        logger.info(f"New subscriber added: {email}")
    else:
        logger.info(f"Subscriber already exists: {email}")
    return jsonify({"message": "Subscription successful", "email": email})

@app.route("/subscribers", methods=["GET"])
async def get_subscribers():
    return jsonify({"subscribers": _subscribers})

@validate_querystring(GamesAllQuery)
@app.route("/games/all", methods=["GET"])
async def get_all_games(query: GamesAllQuery):
    page = query.page
    page_size = query.pageSize
    start_date = query.startDate
    end_date = query.endDate

    all_games = []
    for date_str, games in _games_by_date.items():
        if start_date and date_str < start_date:
            continue
        if end_date and date_str > end_date:
            continue
        for g in games:
            g_copy = g.copy()
            g_copy["date"] = date_str
            all_games.append(g_copy)

    total = len(all_games)
    total_pages = max((total + page_size - 1) // page_size, 1)
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    paged_games = all_games[start_idx:end_idx]

    return jsonify({
        "games": paged_games,
        "pagination": {
            "page": page,
            "pageSize": page_size,
            "totalPages": total_pages,
            "totalGames": total,
        }
    })

@app.route("/games/<date>", methods=["GET"])
async def get_games_by_date(date: str):
    games = _games_by_date.get(date)
    if games is None:
        return jsonify({"date": date, "games": []})
    return jsonify({"date": date, "games": games})

@app.route("/fetch-scores", methods=["POST"])
@validate_request(FetchScoresRequest)
async def fetch_scores(data: FetchScoresRequest):
    date = data.date
    job_id = f"job-{datetime.utcnow().timestamp()}"
    _entity_jobs[job_id] = {"status": "queued", "requestedAt": datetime.utcnow().isoformat()}
    asyncio.create_task(process_fetch_scores(job_id, date))
    return jsonify({
        "message": "Scores fetch job accepted",
        "jobId": job_id,
        "date": date
    })

async def fetch_nba_scores(date: str) -> List[Dict]:
    url = NBA_API_URL.format(date=date)
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.exception(f"Error fetching scores for {date}: {e}")
            return []

async def send_email_notifications(date: str, games: List[Dict], subscribers: List[str]):
    if not subscribers:
        logger.info("No subscribers to send notifications.")
        return
    summary_lines = []
    for game in games:
        home = game.get("HomeTeam", "N/A")
        away = game.get("AwayTeam", "N/A")
        home_score = game.get("HomeTeamScore", "N/A")
        away_score = game.get("AwayTeamScore", "N/A")
        summary_lines.append(f"{away} {away_score} @ {home} {home_score}")
    summary = "\n".join(summary_lines)
    for email in subscribers:
        # TODO: Implement real email sending
        logger.info(f"Sending NBA scores notification to {email} for {date}:\n{summary}")

async def process_fetch_scores(job_id: str, date: str):
    _entity_jobs[job_id]["status"] = "processing"
    _entity_jobs[job_id]["requestedAt"] = datetime.utcnow().isoformat()
    logger.info(f"Started processing job {job_id} for date {date}")
    games = await fetch_nba_scores(date)
    if games:
        _games_by_date[date] = games
        logger.info(f"Stored {len(games)} games for {date}")
    else:
        logger.warning(f"No games fetched for {date}")
    await send_email_notifications(date, games, _subscribers)
    _entity_jobs[job_id]["status"] = "completed"
    logger.info(f"Completed job {job_id} for date {date}")

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)