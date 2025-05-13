```python
import asyncio
import datetime
import logging
from typing import List, Dict

from quart import Quart, request, jsonify
from quart_schema import QuartSchema
import httpx

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# In-memory storage mocks
_subscribers: List[str] = []
_games_storage: Dict[str, List[Dict]] = {}  # key = date string YYYY-MM-DD, value = list of games

# Entity job status for fetch process
entity_job = {}

# External NBA scores API config
NBA_API_KEY = "test"  # Provided test key
NBA_API_URL_TEMPLATE = "https://api.sportsdata.io/v3/nba/scores/json/ScoresBasicFinal/{date}?key=" + NBA_API_KEY


async def fetch_nba_scores_for_date(date_str: str) -> List[Dict]:
    url = NBA_API_URL_TEMPLATE.format(date=date_str)
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, timeout=20.0)
            response.raise_for_status()
            data = response.json()
            # TODO: confirm structure of data returned by API, assume list of games
            return data
        except httpx.HTTPError as e:
            logger.exception(f"HTTP error while fetching NBA scores for {date_str}: {e}")
            return []
        except Exception as e:
            logger.exception(f"Unexpected error while fetching NBA scores for {date_str}: {e}")
            return []


async def send_email_notifications(date_str: str):
    # TODO: Implement real email sending logic
    # For prototype, just log the notification event
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

        # Simplify and store fetched data
        stored_games = []
        for game in nba_data:
            # Extract minimal required fields, fallback keys if missing
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
    """
    Trigger fetching today's NBA scores, storing them, and sending notifications.
    """
    # Use current UTC date for "today"
    date_str = datetime.datetime.utcnow().date().isoformat()
    job_id = f"fetch-{date_str}"

    if job_id in entity_job and entity_job[job_id]["status"] in ["processing", "fetching", "storing", "notifying"]:
        return jsonify({"status": "processing", "message": "Fetch already in progress for today."})

    entity_job[job_id] = {"status": "processing", "requestedAt": datetime.datetime.utcnow().isoformat()}

    # Fire and forget processing task
    asyncio.create_task(process_fetch_scores(job_id, date_str))

    return jsonify({"status": "accepted", "message": f"Fetching NBA scores for {date_str} started."})


@app.route("/subscribe", methods=["POST"])
async def subscribe():
    """
    Add an email to subscriber list.
    """
    try:
        data = await request.get_json()
        email = data.get("email", "").strip().lower()
        if not email:
            return jsonify({"status": "error", "message": "Email is required"}), 400
        if email in _subscribers:
            return jsonify({"status": "success", "message": f"Already subscribed: {email}"})
        _subscribers.append(email)
        logger.info(f"New subscriber added: {email}")
        return jsonify({"status": "success", "message": f"Subscription successful for {email}"})
    except Exception as e:
        logger.exception("Error in /subscribe endpoint")
        return jsonify({"status": "error", "message": "Invalid request"}), 400


@app.route("/subscribers", methods=["GET"])
async def get_subscribers():
    """
    Retrieve list of all subscriber emails.
    """
    return jsonify({"subscribers": _subscribers})


@app.route("/games/all", methods=["GET"])
async def get_all_games():
    """
    Retrieve all stored NBA games, optionally paginated.
    """
    try:
        page = int(request.args.get("page", 1))
        limit = int(request.args.get("limit", 50))
        # Flatten all games by date
        all_games = []
        for games in _games_storage.values():
            all_games.extend(games)

        # Simple pagination
        start = (page - 1) * limit
        end = start + limit
        paged_games = all_games[start:end]

        return jsonify({"games": paged_games})
    except Exception as e:
        logger.exception("Error in /games/all endpoint")
        return jsonify({"games": []})


@app.route("/games/<date_str>", methods=["GET"])
async def get_games_by_date(date_str: str):
    """
    Retrieve all games for a specific date (YYYY-MM-DD).
    """
    games = _games_storage.get(date_str, [])
    return jsonify({"date": date_str, "games": games})


if __name__ == "__main__":
    import sys
    import logging

    logging.basicConfig(stream=sys.stdout, level=logging.INFO)
    app.run(use_reloader=False, debug=True, host="0.0.0.0", port=8000, threaded=True)
```
