```python
import asyncio
import logging
from datetime import datetime
from typing import List, Dict

import httpx
from quart import Quart, request, jsonify
from quart_schema import QuartSchema

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# In-memory storage (async-safe pattern: use asyncio.Lock)
class Storage:
    def __init__(self):
        self._lock = asyncio.Lock()
        self.subscribers: set[str] = set()
        self.games: Dict[str, List[dict]] = {}  # key=date YYYY-MM-DD, value=list of games

    async def add_subscriber(self, email: str) -> bool:
        async with self._lock:
            if email in self.subscribers:
                return False
            self.subscribers.add(email)
            return True

    async def list_subscribers(self) -> List[str]:
        async with self._lock:
            return list(self.subscribers)

    async def save_games(self, date: str, games: List[dict]):
        async with self._lock:
            self.games[date] = games

    async def get_games_all(self) -> List[dict]:
        async with self._lock:
            # Flatten all games from all dates
            all_games = []
            for games_list in self.games.values():
                all_games.extend(games_list)
            return all_games

    async def get_games_by_date(self, date: str) -> List[dict]:
        async with self._lock:
            return self.games.get(date, [])


storage = Storage()


NBA_API_KEY = "test"  # Provided in requirement
NBA_API_URL = "https://api.sportsdata.io/v3/nba/scores/json/ScoresBasicFinal/{date}?key=" + NBA_API_KEY


async def fetch_nba_scores(date: str) -> List[dict]:
    """Fetch NBA scores asynchronously from real API."""
    url = NBA_API_URL.format(date=date)
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            data = resp.json()
            # TODO: Check data format correctness, adapt if needed
            return data  # Assuming data is list of game dicts
    except Exception as e:
        logger.exception(f"Failed to fetch NBA scores for {date}: {e}")
        return []


async def send_email(to_emails: List[str], subject: str, body: str):
    """
    Mock sending email asynchronously.
    TODO: Replace with real email service integration.
    """
    await asyncio.sleep(0.1)  # simulate network delay
    logger.info(f"Sending email to {len(to_emails)} subscribers:\nSubject: {subject}\nBody:\n{body}")


def build_email_body(date: str, games: List[dict]) -> str:
    """Creates a plain text summary of the day's games for email."""
    if not games:
        return f"No NBA games found for {date}."

    lines = [f"NBA Scores for {date}:\n"]
    for g in games:
        # Example keys, adjust based on actual API response:
        home = g.get("HomeTeam") or g.get("HomeTeamName") or g.get("HomeTeamID") or "Home"
        away = g.get("AwayTeam") or g.get("AwayTeamName") or g.get("AwayTeamID") or "Away"
        home_score = g.get("HomeTeamScore") or g.get("HomeScore") or g.get("HomeTeamPoints") or "N/A"
        away_score = g.get("AwayTeamScore") or g.get("AwayScore") or g.get("AwayTeamPoints") or "N/A"
        lines.append(f"{away} @ {home} — {away_score}:{home_score}")
    return "\n".join(lines)


async def process_fetch_store_notify(date: str):
    logger.info(f"Starting fetch/store/notify for date {date}")
    games = await fetch_nba_scores(date)
    if not games:
        logger.warning(f"No games data fetched for {date}")
    await storage.save_games(date, games)

    subscribers = await storage.list_subscribers()
    if not subscribers:
        logger.info("No subscribers to notify.")
        return

    email_body = build_email_body(date, games)
    subject = f"NBA Scores for {date}"

    # Send emails in fire-and-forget fashion but await to log errors
    try:
        await send_email(subscribers, subject, email_body)
        logger.info(f"Email notifications sent for {date} to {len(subscribers)} subscribers.")
    except Exception as e:
        logger.exception(f"Failed sending emails for {date}: {e}")


@app.route("/subscribe", methods=["POST"])
async def subscribe():
    data = await request.get_json(force=True)
    email = data.get("email")
    if not email:
        return jsonify({"message": "Email is required"}), 400

    added = await storage.add_subscriber(email)
    if not added:
        return jsonify({"message": "Email already subscribed", "email": email}), 409
    return jsonify({"message": "Subscription successful", "email": email}), 201


@app.route("/subscribers", methods=["GET"])
async def get_subscribers():
    subscribers = await storage.list_subscribers()
    return jsonify({"subscribers": subscribers})


@app.route("/fetch-scores", methods=["POST"])
async def fetch_scores():
    data = await request.get_json(force=True)
    date = data.get("date")
    if not date:
        return jsonify({"message": "Date is required"}), 400

    # Validate date format YYYY-MM-DD
    try:
        datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        return jsonify({"message": "Invalid date format, expected YYYY-MM-DD"}), 400

    # Fire and forget processing
    asyncio.create_task(process_fetch_store_notify(date))
    return jsonify({"message": f"Scores fetch started for {date}"}), 202


@app.route("/games/all", methods=["GET"])
async def get_all_games():
    page = request.args.get("page", default=1, type=int)
    limit = request.args.get("limit", default=50, type=int)
    if page < 1 or limit < 1:
        return jsonify({"message": "Page and limit must be positive integers"}), 400

    all_games = await storage.get_games_all()
    total = len(all_games)
    start = (page - 1) * limit
    end = start + limit
    paginated = all_games[start:end]

    return jsonify({
        "games": paginated,
        "page": page,
        "limit": limit,
        "total": total
    })


@app.route("/games/<date>", methods=["GET"])
async def get_games_by_date(date):
    try:
        datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        return jsonify({"message": "Invalid date format, expected YYYY-MM-DD"}), 400

    games = await storage.get_games_by_date(date)
    return jsonify({
        "date": date,
        "games": games
    })


if __name__ == '__main__':
    import os
    logging.basicConfig(level=logging.INFO)
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
```
