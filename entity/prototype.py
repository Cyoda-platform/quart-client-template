```python
import asyncio
import datetime
import json
import logging
from typing import Dict, List, Optional

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# Constants
API_KEY = "test"
NBA_API_URL = "https://api.sportsdata.io/v3/nba/scores/json/ScoresBasicFinal/{date}?key={key}"
SCHEDULER_TIME_UTC = "18:00"  # 6:00 PM UTC, fixed by application property

# In-memory "persistence" - replace with proper DB in future
_subscribers: Dict[str, Dict] = {}
# email -> {"notificationType": "summary"|"full"}

_game_data_cache: Dict[str, List[Dict]] = {}
# date (YYYY-MM-DD) -> list of games

# To avoid global keyword in async code, wrap caches in objects
class Storage:
    def __init__(self):
        self.subscribers: Dict[str, Dict] = {}
        self.game_data: Dict[str, List[Dict]] = {}

storage = Storage()


@app.route("/subscribe", methods=["POST"])
async def subscribe():
    try:
        data = await request.get_json()
        email = data.get("email")
        notification_type = data.get("notificationType", "summary")
        if not email or notification_type not in ("summary", "full"):
            return jsonify({"error": "Invalid email or notificationType"}), 400

        storage.subscribers[email] = {"notificationType": notification_type}
        logger.info(f"New subscription: {email} with preference {notification_type}")
        return jsonify({
            "message": "Subscription successful",
            "email": email,
            "notificationType": notification_type
        })
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to subscribe"}), 500


@app.route("/subscribers", methods=["GET"])
async def get_subscribers():
    try:
        subs = [
            {"email": email, "notificationType": pref["notificationType"]}
            for email, pref in storage.subscribers.items()
        ]
        return jsonify(subs)
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to retrieve subscribers"}), 500


@app.route("/games/fetch", methods=["POST"])
async def fetch_and_store_games():
    try:
        data = await request.get_json()
        date_str = data.get("date")
        if not date_str:
            return jsonify({"error": "Date parameter is required"}), 400

        # Validate date format
        try:
            datetime.datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            return jsonify({"error": "Date must be in YYYY-MM-DD format"}), 400

        # Fire and forget fetching and processing
        job_id = f"fetch_{date_str}"
        logger.info(f"Starting fetch job {job_id}")
        asyncio.create_task(_fetch_process_and_notify(date_str))
        return jsonify({
            "message": "Scores fetch started",
            "date": date_str
        })
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to trigger fetch"}), 500


@app.route("/games/all", methods=["GET"])
async def get_all_games():
    try:
        date_filter = request.args.get("date")
        team_filter = request.args.get("team")
        offset = request.args.get("offset", default=0, type=int)
        limit = request.args.get("limit", default=10, type=int)

        # Collect filtered games
        all_games = []
        if date_filter:
            games_for_date = storage.game_data.get(date_filter, [])
            all_games.extend(games_for_date)
        else:
            for games in storage.game_data.values():
                all_games.extend(games)

        if team_filter:
            team_filter_lower = team_filter.lower()
            all_games = [
                g for g in all_games
                if team_filter_lower in g.get("HomeTeam", "").lower()
                or team_filter_lower in g.get("AwayTeam", "").lower()
            ]

        total = len(all_games)
        paged_games = all_games[offset : offset + limit]

        # Normalize response keys to camelCase per spec
        def normalize_game(g: Dict) -> Dict:
            return {
                "gameId": g.get("GameID"),
                "date": g.get("Day"),
                "homeTeam": g.get("HomeTeam"),
                "awayTeam": g.get("AwayTeam"),
                "homeScore": g.get("HomeTeamScore"),
                "awayScore": g.get("AwayTeamScore"),
                "status": g.get("Status"),
            }

        response_games = [normalize_game(g) for g in paged_games]

        return jsonify({
            "games": response_games,
            "pagination": {
                "offset": offset,
                "limit": limit,
                "total": total
            }
        })
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to retrieve games"}), 500


@app.route("/games/<date>", methods=["GET"])
async def get_games_by_date(date: str):
    try:
        # Validate date format
        try:
            datetime.datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            return jsonify({"error": "Date must be in YYYY-MM-DD format"}), 400

        games_for_date = storage.game_data.get(date, [])

        def normalize_game(g: Dict) -> Dict:
            return {
                "gameId": g.get("GameID"),
                "date": g.get("Day"),
                "homeTeam": g.get("HomeTeam"),
                "awayTeam": g.get("AwayTeam"),
                "homeScore": g.get("HomeTeamScore"),
                "awayScore": g.get("AwayTeamScore"),
                "status": g.get("Status"),
            }

        response_games = [normalize_game(g) for g in games_for_date]

        return jsonify({
            "games": response_games,
            "pagination": {
                "offset": 0,
                "limit": len(response_games),
                "total": len(response_games)
            }
        })
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to retrieve games"}), 500


async def _fetch_process_and_notify(date_str: str):
    """Fetch NBA scores from external API, store locally, send emails."""
    try:
        url = NBA_API_URL.format(date=date_str, key=API_KEY)
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            games = resp.json()
            logger.info(f"Fetched {len(games)} games for {date_str}")

        # Store in local JSON cache (in-memory)
        storage.game_data[date_str] = games

        # Send notifications (mocked)
        await _send_notifications(date_str, games)

    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error when fetching NBA scores: {e}")
    except Exception as e:
        logger.exception(e)


async def _send_notifications(date_str: str, games: List[Dict]):
    """Send emails to subscribers respecting their preferences."""
    try:
        subscribers = storage.subscribers.copy()
        if not subscribers:
            logger.info("No subscribers to notify.")
            return

        for email, pref in subscribers.items():
            notification_type = pref.get("notificationType", "summary")
            content = _build_email_content(date_str, games, notification_type)
            # TODO: Implement real email sending here
            logger.info(f"Sending {notification_type} email to {email} for {date_str}")
            # Simulate async send delay
            await asyncio.sleep(0.1)

    except Exception as e:
        logger.exception(e)


def _build_email_content(date_str: str, games: List[Dict], notification_type: str) -> str:
    """Build email content in HTML format."""
    if notification_type == "summary":
        total_games = len(games)
        total_points = sum(g.get("HomeTeamScore", 0) + g.get("AwayTeamScore", 0) for g in games)
        content = f"""
        <html>
        <body>
            <h2>NBA Summary for {date_str}</h2>
            <p>Total games played: {total_games}</p>
            <p>Total points scored: {total_points}</p>
        </body>
        </html>
        """
    else:  # full details
        rows = ""
        for g in games:
            rows += f"<tr><td>{g.get('HomeTeam')}</td><td>{g.get('HomeTeamScore')}</td>" \
                    f"<td>vs</td><td>{g.get('AwayTeam')}</td><td>{g.get('AwayTeamScore')}</td>" \
                    f"<td>{g.get('Status')}</td></tr>"

        content = f"""
        <html>
        <body>
            <h2>NBA Full Details for {date_str}</h2>
            <table border="1" cellpadding="5" cellspacing="0">
                <tr><th>Home Team</th><th>Score</th><th></th><th>Away Team</th><th>Score</th><th>Status</th></tr>
                {rows}
            </table>
        </body>
        </html>
        """
    return content


async def _scheduler_loop():
    """Simple scheduler loop to run daily fetch at fixed UTC time."""
    while True:
        now = datetime.datetime.utcnow()
        target_time = datetime.datetime.strptime(SCHEDULER_TIME_UTC, "%H:%M").time()
        next_run = datetime.datetime.combine(now.date(), target_time)
        if now.time() > target_time:
            next_run += datetime.timedelta(days=1)
        wait_seconds = (next_run - now).total_seconds()
        logger.info(f"Scheduler sleeping for {wait_seconds:.1f} seconds until {next_run} UTC")
        await asyncio.sleep(wait_seconds)

        today_str = datetime.datetime.utcnow().strftime("%Y-%m-%d")
        logger.info(f"Scheduler triggering fetch for {today_str}")
        # Fire and forget fetch and notify
        asyncio.create_task(_fetch_process_and_notify(today_str))


@app.before_serving
async def startup():
    # Start scheduler task
    app.add_background_task(_scheduler_loop)


if __name__ == '__main__':
    import sys
    logging.basicConfig(level=logging.INFO, stream=sys.stdout,
                        format="%(asctime)s %(levelname)s %(name)s - %(message)s")
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
```
