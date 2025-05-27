```python
import asyncio
import logging
from datetime import datetime
from typing import List, Dict, Optional

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# In-memory caches simulating persistence
_subscribers: List[str] = []
_games_by_date: Dict[str, List[Dict]] = {}
_entity_jobs: Dict[str, Dict] = {}  # job_id -> status info


API_KEY = "test"
NBA_API_URL = "https://api.sportsdata.io/v3/nba/scores/json/ScoresBasicFinal/{date}?key=" + API_KEY


async def fetch_nba_scores(date: str) -> List[Dict]:
    url = NBA_API_URL.format(date=date)
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            # TODO: Validate and normalize data structure if needed
            return data
        except httpx.HTTPError as e:
            logger.exception(f"HTTP error while fetching scores for {date}: {e}")
            return []
        except Exception as e:
            logger.exception(f"Unexpected error fetching scores for {date}: {e}")
            return []


async def send_email_notifications(date: str, games: List[Dict], subscribers: List[str]):
    # TODO: Implement real email sending via SMTP or an email service provider
    # For prototype, just log the notification
    if not subscribers:
        logger.info("No subscribers to send notifications.")
        return

    summary_lines = []
    for game in games:
        # Basic summary line, adapt keys based on actual data
        home = game.get("HomeTeam", "N/A")
        away = game.get("AwayTeam", "N/A")
        home_score = game.get("HomeTeamScore", "N/A")
        away_score = game.get("AwayTeamScore", "N/A")
        summary_lines.append(f"{away} {away_score} @ {home} {home_score}")

    summary = "\n".join(summary_lines)
    for email in subscribers:
        logger.info(f"Sending NBA scores notification to {email} for {date}:\n{summary}")


async def process_fetch_scores(job_id: str, date: str):
    _entity_jobs[job_id]["status"] = "processing"
    _entity_jobs[job_id]["requestedAt"] = datetime.utcnow().isoformat()
    logger.info(f"Started processing job {job_id} for date {date}")

    games = await fetch_nba_scores(date)
    if games:
        # Save games locally (override or append)
        _games_by_date[date] = games
        logger.info(f"Stored {len(games)} games for {date}")
    else:
        logger.warning(f"No games fetched for {date}")

    # Send notifications
    await send_email_notifications(date, games, _subscribers)

    _entity_jobs[job_id]["status"] = "completed"
    logger.info(f"Completed job {job_id} for date {date}")


@app.route("/subscribe", methods=["POST"])
async def subscribe():
    data = await request.get_json(force=True)
    email = data.get("email")
    if not email or not isinstance(email, str):
        return jsonify({"error": "Invalid or missing email"}), 400

    if email not in _subscribers:
        _subscribers.append(email)
        logger.info(f"New subscriber added: {email}")
    else:
        logger.info(f"Subscriber already exists: {email}")

    return jsonify({"message": "Subscription successful", "email": email})


@app.route("/subscribers", methods=["GET"])
async def get_subscribers():
    return jsonify({"subscribers": _subscribers})


@app.route("/games/all", methods=["GET"])
async def get_all_games():
    # Optional query params: page, pageSize, startDate, endDate
    page = int(request.args.get("page", 1))
    page_size = int(request.args.get("pageSize", 20))
    start_date = request.args.get("startDate")
    end_date = request.args.get("endDate")

    # Flatten all games and filter by date range if provided
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
    # Expect date format YYYY-MM-DD
    games = _games_by_date.get(date)
    if games is None:
        return jsonify({"date": date, "games": []})
    return jsonify({"date": date, "games": games})


@app.route("/fetch-scores", methods=["POST"])
async def fetch_scores():
    data = await request.get_json(force=True)
    date = data.get("date")
    if not date:
        return jsonify({"error": "Missing 'date' in request body"}), 400

    job_id = f"job-{datetime.utcnow().timestamp()}"
    _entity_jobs[job_id] = {"status": "queued", "requestedAt": datetime.utcnow().isoformat()}

    # Fire and forget the processing task
    asyncio.create_task(process_fetch_scores(job_id, date))

    return jsonify({
        "message": "Scores fetch job accepted",
        "jobId": job_id,
        "date": date
    })


if __name__ == '__main__':
    import logging
    logging.basicConfig(level=logging.INFO)
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
```
