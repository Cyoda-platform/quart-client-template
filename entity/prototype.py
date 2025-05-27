from dataclasses import dataclass
from typing import Optional, List, Dict
import asyncio
import logging
from datetime import datetime, timezone

import httpx
from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request, validate_querystring

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# Data models for request validation
@dataclass
class SubscribeRequest:
    email: str

@dataclass
class FetchScoresRequest:
    date: Optional[str] = None

@dataclass
class PageParams:
    page: Optional[int] = 1
    limit: Optional[int] = 20

# In-memory cache with async lock
class Cache:
    def __init__(self):
        self._lock = asyncio.Lock()
        self.subscribers: List[str] = []
        self.games: Dict[str, List[dict]] = {}

    async def add_subscriber(self, email: str) -> None:
        async with self._lock:
            if email not in self.subscribers:
                self.subscribers.append(email)

    async def get_subscribers(self) -> List[str]:
        async with self._lock:
            return list(self.subscribers)

    async def store_games(self, date: str, games_data: List[dict]) -> None:
        async with self._lock:
            self.games[date] = games_data

    async def get_games_by_date(self, date: str) -> List[dict]:
        async with self._lock:
            return self.games.get(date, [])

    async def get_all_games(self) -> List[dict]:
        async with self._lock:
            all_games = []
            for games in self.games.values():
                all_games.extend(games)
            return all_games

cache = Cache()

API_KEY = "test"
API_ENDPOINT_TEMPLATE = "https://api.sportsdata.io/v3/nba/scores/json/ScoresBasicFinal/{date}?key={key}"

async def send_email(to_emails: List[str], subject: str, content: str):
    logger.info(f"Sending Email to {len(to_emails)} subscribers with subject: {subject}")
    await asyncio.sleep(0.1)
    # TODO: Integrate with real email provider (e.g. SMTP, SendGrid, SES)
    logger.info("Email sent.")

async def fetch_scores_for_date(date: str) -> List[dict]:
    url = API_ENDPOINT_TEMPLATE.format(date=date, key=API_KEY)
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, timeout=20)
            response.raise_for_status()
            data = response.json()
            logger.info(f"Fetched {len(data)} games for {date} from external API.")
            return data
        except httpx.HTTPError as e:
            logger.exception(f"HTTP error while fetching scores for {date}: {e}")
            return []
        except Exception as e:
            logger.exception(f"Unexpected error while fetching scores for {date}: {e}")
            return []

def format_email_content(date: str, games: List[dict]) -> str:
    if not games:
        return f"No NBA games found for {date}."
    lines = [f"NBA Scores for {date}:\n"]
    for g in games:
        home_team = g.get("HomeTeam", "N/A")
        away_team = g.get("AwayTeam", "N/A")
        home_score = g.get("HomeTeamScore", "N/A")
        away_score = g.get("AwayTeamScore", "N/A")
        lines.append(f"{away_team} @ {home_team} — {away_score} : {home_score}")
    return "\n".join(lines)

@app.route("/subscribe", methods=["POST"])
# Workaround: place validate_request last for POST due to quart-schema defect
@validate_request(SubscribeRequest)
async def subscribe(data: SubscribeRequest):
    email = data.email.strip().lower()
    await cache.add_subscriber(email)
    logger.info(f"New subscription added: {email}")
    return jsonify({"message": "Subscription successful", "email": email})

@app.route("/subscribers", methods=["GET"])
async def get_subscribers():
    subs = await cache.get_subscribers()
    return jsonify({"subscribers": subs})

# Workaround: place validate_querystring first for GET due to quart-schema defect
@validate_querystring(PageParams)
@app.route("/games/all", methods=["GET"])
async def get_all_games():
    try:
        page = int(request.args.get("page", 1))
        limit = int(request.args.get("limit", 20))
        if page < 1 or limit < 1:
            raise ValueError
    except ValueError:
        return jsonify({"error": "Invalid pagination parameters"}), 400

    all_games = await cache.get_all_games()
    total = len(all_games)
    start = (page - 1) * limit
    end = start + limit
    paged_games = all_games[start:end]

    return jsonify({
        "games": paged_games,
        "page": page,
        "limit": limit,
        "total": total
    })

@app.route("/games/<date>", methods=["GET"])
async def get_games_by_date(date):
    try:
        datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        return jsonify({"error": "Invalid date format, expected YYYY-MM-DD"}), 400

    games = await cache.get_games_by_date(date)
    return jsonify({"date": date, "games": games})

@app.route("/fetch-scores", methods=["POST"])
# Workaround: place validate_request last for POST due to quart-schema defect
@validate_request(FetchScoresRequest)
async def fetch_scores(data: FetchScoresRequest):
    date = data.date
    if date:
        try:
            datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            return jsonify({"error": "Invalid date format, expected YYYY-MM-DD"}), 400
    else:
        date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    try:
        result = await process_scores_and_notify(date)
        return jsonify(result)
    except Exception:
        logger.exception("Error in fetch_scores endpoint")
        return jsonify({"error": "Failed to fetch and process scores"}), 500

async def process_scores_and_notify(date: str) -> dict:
    games = await fetch_scores_for_date(date)
    if not games:
        return {"message": "No games fetched or error occurred", "date": date, "games_fetched": 0}

    await cache.store_games(date, games)
    subscribers = await cache.get_subscribers()
    if not subscribers:
        logger.info("No subscribers to notify")
        return {"message": "Scores fetched and stored, but no subscribers to notify", "date": date, "games_fetched": len(games)}

    email_content = format_email_content(date, games)
    subject = f"NBA Scores for {date}"
    await send_email(subscribers, subject, email_content)

    return {"message": "Scores fetched, stored, and notifications sent", "date": date, "games_fetched": len(games)}

if __name__ == '__main__':
    import sys
    logging.basicConfig(
        stream=sys.stdout,
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)