from dataclasses import dataclass
import asyncio
import logging
from datetime import datetime
from typing import List, Dict

import httpx
from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request, validate_querystring

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# Data classes for request validation
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

# In-memory storage (async-safe)
class Storage:
    def __init__(self):
        self._lock = asyncio.Lock()
        self.subscribers: set[str] = set()
        self.games: Dict[str, List[dict]] = {}

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
            all_games = []
            for games_list in self.games.values():
                all_games.extend(games_list)
            return all_games

    async def get_games_by_date(self, date: str) -> List[dict]:
        async with self._lock:
            return self.games.get(date, [])

storage = Storage()

NBA_API_KEY = "test"
NBA_API_URL = "https://api.sportsdata.io/v3/nba/scores/json/ScoresBasicFinal/{date}?key=" + NBA_API_KEY

async def fetch_nba_scores(date: str) -> List[dict]:
    url = NBA_API_URL.format(date=date)
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        logger.exception(f"Failed to fetch NBA scores for {date}: {e}")
        return []

async def send_email(to_emails: List[str], subject: str, body: str):
    await asyncio.sleep(0.1)
    logger.info(f"Mock email to {len(to_emails)}: {subject}\n{body}")

def build_email_body(date: str, games: List[dict]) -> str:
    if not games:
        return f"No NBA games found for {date}."
    lines = [f"NBA Scores for {date}:\n"]
    for g in games:
        home = g.get("HomeTeam") or "Home"
        away = g.get("AwayTeam") or "Away"
        home_score = g.get("HomeTeamScore") or "N/A"
        away_score = g.get("AwayTeamScore") or "N/A"
        lines.append(f"{away} @ {home} — {away_score}:{home_score}")
    return "\n".join(lines)

async def process_fetch_store_notify(date: str):
    logger.info(f"Starting process for {date}")
    games = await fetch_nba_scores(date)
    await storage.save_games(date, games)
    subscribers = await storage.list_subscribers()
    if not subscribers:
        logger.info("No subscribers to notify.")
        return
    body = build_email_body(date, games)
    subject = f"NBA Scores for {date}"
    try:
        await send_email(subscribers, subject, body)
        logger.info(f"Notified {len(subscribers)} subscribers.")
    except Exception as e:
        logger.exception(f"Error sending emails: {e}")

@app.route("/subscribe", methods=["POST"])
@validate_request(Subscriber)  # validate_request after route for POST (workaround)
async def subscribe(data: Subscriber):
    added = await storage.add_subscriber(data.email)
    if not added:
        return jsonify({"message": "Email already subscribed", "email": data.email}), 409
    return jsonify({"message": "Subscription successful", "email": data.email}), 201

@app.route("/subscribers", methods=["GET"])
async def get_subscribers():
    subs = await storage.list_subscribers()
    return jsonify({"subscribers": subs})

@app.route("/fetch-scores", methods=["POST"])
@validate_request(FetchScores)  # validate_request after route for POST (workaround)
async def fetch_scores(data: FetchScores):
    try:
        datetime.strptime(data.date, "%Y-%m-%d")
    except ValueError:
        return jsonify({"message": "Invalid date format, expected YYYY-MM-DD"}), 400
    asyncio.create_task(process_fetch_store_notify(data.date))
    return jsonify({"message": f"Scores fetch started for {data.date}"}), 202

@validate_querystring(GamesQuery)  # validate_querystring before route for GET (workaround)
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
    return jsonify({
        "games": all_games[start:end],
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
    return jsonify({"date": date, "games": games})

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)