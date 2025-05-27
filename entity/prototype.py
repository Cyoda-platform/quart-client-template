```python
import asyncio
import logging
from datetime import datetime
from typing import List, Dict, Optional

import httpx
from quart import Quart, request, jsonify
from quart_schema import QuartSchema

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# In-memory mock persistence
# Use asyncio.Lock to avoid race conditions on shared state
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
            else:
                logger.info(f"Subscriber {email} already exists")
                return False

    async def remove_subscriber(self, email: str) -> bool:
        async with self._lock:
            if email in self._subscribers:
                self._subscribers.remove(email)
                logger.info(f"Removed subscriber: {email}")
                return True
            else:
                logger.info(f"Attempted to remove non-existing subscriber: {email}")
                return False

    async def list_subscribers(self) -> List[str]:
        async with self._lock:
            return list(self._subscribers)

    async def store_games(self, date: str, games: List[Dict]):
        async with self._lock:
            self._games_by_date[date] = games
            logger.info(f"Stored {len(games)} games for date {date}")

    async def get_games_by_date(self, date: str) -> Optional[List[Dict]]:
        async with self._lock:
            return self._games_by_date.get(date, [])

    async def get_all_games(self, start_date: Optional[str] = None, end_date: Optional[str] = None) -> List[Dict]:
        async with self._lock:
            all_games = []
            for date_str, games in self._games_by_date.items():
                if start_date and date_str < start_date:
                    continue
                if end_date and date_str > end_date:
                    continue
                all_games.extend(games)
            return all_games


storage = Storage()

# Real API details
API_KEY = "test"  # Provided in spec; replace if needed
NBA_API_URL_TEMPLATE = "https://api.sportsdata.io/v3/nba/scores/json/ScoresBasicFinal/{date}?key=" + API_KEY

# Email sending mock - TODO: Replace with real email sending mechanism
async def send_email(to_email: str, subject: str, html_content: str):
    logger.info(f"Sending email to {to_email} with subject '{subject}'")
    # TODO: Implement real email sending
    await asyncio.sleep(0.1)  # simulate network delay


# Build HTML summary for daily games
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


# Background task to fetch, store, notify
async def process_scores_fetch(date: str):
    try:
        url = NBA_API_URL_TEMPLATE.format(date=date)
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, timeout=20)
            resp.raise_for_status()
            games = resp.json()
            # games is expected to be a list of dicts

        # Store games
        await storage.store_games(date, games)

        # Notify subscribers
        subscribers = await storage.list_subscribers()
        if subscribers:
            summary_html = build_html_summary(date, games)
            send_tasks = []
            for email in subscribers:
                send_tasks.append(send_email(email, f"NBA Scores for {date}", summary_html))
            await asyncio.gather(*send_tasks)

        logger.info(f"Fetched and notified for date {date}: {len(games)} games, {len(subscribers)} subscribers")
        return {"gamesStored": len(games), "notificationsSent": len(subscribers)}

    except Exception as e:
        logger.exception(f"Error processing scores fetch for date {date}: {e}")
        raise


@app.route("/subscribe", methods=["POST"])
async def subscribe():
    data = await request.get_json()
    email = data.get("email")
    if not email:
        return jsonify({"message": "Email is required"}), 400

    added = await storage.add_subscriber(email)
    if added:
        return jsonify({"message": "Subscription successful", "email": email}), 201
    else:
        return jsonify({"message": "Email already subscribed", "email": email}), 200


@app.route("/unsubscribe", methods=["POST"])
async def unsubscribe():
    data = await request.get_json()
    email = data.get("email")
    if not email:
        return jsonify({"message": "Email is required"}), 400

    removed = await storage.remove_subscriber(email)
    if removed:
        return jsonify({"message": "Unsubscribed successfully", "email": email}), 200
    else:
        return jsonify({"message": "Email not found in subscribers", "email": email}), 404


@app.route("/subscribers", methods=["GET"])
async def get_subscribers():
    subs = await storage.list_subscribers()
    return jsonify({"subscribers": subs}), 200


@app.route("/scores/fetch", methods=["POST"])
async def fetch_scores():
    data = await request.get_json()
    date = data.get("date")
    if not date:
        return jsonify({"message": "Date is required in YYYY-MM-DD format"}), 400
    # Basic validation of date format
    try:
        datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        return jsonify({"message": "Invalid date format, expected YYYY-MM-DD"}), 400

    # Fire and forget the processing task:
    # In prototype, we wait for completion to return meaningful response
    try:
        result = await process_scores_fetch(date)
        return jsonify({
            "message": "Scores fetched and notifications sent",
            "date": date,
            **result
        }), 200
    except Exception:
        return jsonify({"message": "Failed to fetch or process scores"}), 500


@app.route("/games/all", methods=["GET"])
async def get_all_games():
    # Optional query params
    page = int(request.args.get("page", 1))
    page_size = int(request.args.get("pageSize", 10))
    start_date = request.args.get("startDate")
    end_date = request.args.get("endDate")

    all_games = await storage.get_all_games(start_date, end_date)
    total = len(all_games)

    # Paginate
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    paged_games = all_games[start_idx:end_idx]

    return jsonify({
        "games": paged_games,
        "page": page,
        "pageSize": page_size,
        "totalGames": total
    }), 200


@app.route("/games/<string:date>", methods=["GET"])
async def get_games_by_date(date):
    # Validate date format
    try:
        datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        return jsonify({"message": "Invalid date format, expected YYYY-MM-DD"}), 400

    games = await storage.get_games_by_date(date)
    return jsonify({
        "date": date,
        "games": games
    }), 200


if __name__ == '__main__':
    import sys
    import logging

    logging.basicConfig(stream=sys.stdout, level=logging.INFO,
                        format="%(asctime)s - %(levelname)s - %(message)s")

    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
```
