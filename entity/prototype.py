import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import List, Dict, Optional

import httpx
from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# Data classes for request validation
@dataclass
class EmailBody:
    email: str

@dataclass
class DateBody:
    date: str

# In-memory mock persistence
class Storage:
    def __init__(self):
        self._subscribers: List[str] = []
        self._games_by_date: Dict[str, List[Dict]] = {}
        self._lock = asyncio.Lock()

    async def add_subscriber(self, email: str) -> bool:
        async with self._lock:
            if email not in self._subscribers:
                self._subscribers.append(email)
                logger.info(f"Added subscriber: {email}")
                return True
            return False

    async def remove_subscriber(self, email: str) -> bool:
        async with self._lock:
            if email in self._subscribers:
                self._subscribers.remove(email)
                logger.info(f"Removed subscriber: {email}")
                return True
            return False

    async def list_subscribers(self) -> List[str]:
        async with self._lock:
            return list(self._subscribers)

    async def store_games(self, date: str, games: List[Dict]):
        async with self._lock:
            self._games_by_date[date] = games
            logger.info(f"Stored {len(games)} games for date {date}")

    async def get_games_by_date(self, date: str) -> List[Dict]:
        async with self._lock:
            return self._games_by_date.get(date, [])

    async def get_all_games(self, start_date: Optional[str] = None, end_date: Optional[str] = None) -> List[Dict]:
        async with self._lock:
            all_games = []
            for date_str, games in self._games_by_date.items():
                if start_date and date_str < start_date: continue
                if end_date and date_str > end_date: continue
                all_games.extend(games)
            return all_games

storage = Storage()

API_KEY = "test"
NBA_API_URL_TEMPLATE = "https://api.sportsdata.io/v3/nba/scores/json/ScoresBasicFinal/{date}?key=" + API_KEY

async def send_email(to_email: str, subject: str, html_content: str):
    logger.info(f"Sending email to {to_email} with subject '{subject}'")
    # TODO: Implement real email sending
    await asyncio.sleep(0.1)

def build_html_summary(date: str, games: List[Dict]) -> str:
    html = f"<h2>NBA Scores for {date}</h2><ul>"
    for g in games:
        home = g.get("HomeTeam", "N/A")
        away = g.get("AwayTeam", "N/A")
        home_score = g.get("HomeTeamScore", "N/A")
        away_score = g.get("AwayTeamScore", "N/A")
        status = g.get("Status", "")
        html += f"<li>{away} @ {home} : {away_score} - {home_score} ({status})</li>"
    html += "</ul>"
    return html

async def process_scores_fetch(date: str):
    try:
        url = NBA_API_URL_TEMPLATE.format(date=date)
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, timeout=20)
            resp.raise_for_status()
            games = resp.json()
        await storage.store_games(date, games)
        subscribers = await storage.list_subscribers()
        if subscribers:
            summary_html = build_html_summary(date, games)
            await asyncio.gather(*(send_email(email, f"NBA Scores for {date}", summary_html) for email in subscribers))
        return {"gamesStored": len(games), "notificationsSent": len(subscribers)}
    except Exception as e:
        logger.exception(e)
        raise

@app.route("/subscribe", methods=["POST"])
@validate_request(EmailBody)  # workaround: place validate_request after route for POST
async def subscribe(data: EmailBody):
    added = await storage.add_subscriber(data.email)
    if added:
        return jsonify({"message": "Subscription successful", "email": data.email}), 201
    return jsonify({"message": "Email already subscribed", "email": data.email}), 200

@app.route("/unsubscribe", methods=["POST"])
@validate_request(EmailBody)  # workaround: place validate_request after route for POST
async def unsubscribe(data: EmailBody):
    removed = await storage.remove_subscriber(data.email)
    if removed:
        return jsonify({"message": "Unsubscribed successfully", "email": data.email}), 200
    return jsonify({"message": "Email not found in subscribers", "email": data.email}), 404

@app.route("/subscribers", methods=["GET"])
async def get_subscribers():
    subs = await storage.list_subscribers()
    return jsonify({"subscribers": subs}), 200

@app.route("/scores/fetch", methods=["POST"])
@validate_request(DateBody)  # workaround: place validate_request after route for POST
async def fetch_scores(data: DateBody):
    try:
        datetime.strptime(data.date, "%Y-%m-%d")
    except ValueError:
        return jsonify({"message": "Invalid date format, expected YYYY-MM-DD"}), 400
    try:
        result = await process_scores_fetch(data.date)
        return jsonify({"message": "Scores fetched and notifications sent", "date": data.date, **result}), 200
    except:
        return jsonify({"message": "Failed to fetch or process scores"}), 500

@app.route("/games/all", methods=["GET"])
async def get_all_games():
    page = int(request.args.get("page", 1))
    page_size = int(request.args.get("pageSize", 10))
    start_date = request.args.get("startDate")
    end_date = request.args.get("endDate")
    all_games = await storage.get_all_games(start_date, end_date)
    total = len(all_games)
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    return jsonify({"games": all_games[start_idx:end_idx], "page": page, "pageSize": page_size, "totalGames": total}), 200

@app.route("/games/<string:date>", methods=["GET"])
async def get_games_by_date(date):
    try:
        datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        return jsonify({"message": "Invalid date format, expected YYYY-MM-DD"}), 400
    games = await storage.get_games_by_date(date)
    return jsonify({"date": date, "games": games}), 200

if __name__ == '__main__':
    import sys
    logging.basicConfig(stream=sys.stdout, level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)