```python
import asyncio
import datetime
import logging
from typing import Dict, List, Optional

import httpx
from quart import Quart, request, jsonify
from quart_schema import QuartSchema

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# --- In-memory "database" ---
# Structure:
# subscribers: Dict[email, notificationType]
# games: Dict[date_str, List[game_dict]]
subscribers: Dict[str, str] = {}
games: Dict[str, List[Dict]] = {}

# Constants
API_KEY = "test"  # Provided in requirement
API_URL = "https://api.sportsdata.io/v3/nba/scores/json/ScoresBasicFinal/{date}?key={key}"

# Helper functions


async def fetch_nba_scores(date: str) -> Optional[List[Dict]]:
    url = API_URL.format(date=date, key=API_KEY)
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, timeout=20.0)
            resp.raise_for_status()
            data = resp.json()
            # Expecting a list of game dicts per SportsData.io API docs
            return data
    except httpx.HTTPError as e:
        logger.exception(f"Failed to fetch NBA scores for {date}: {e}")
        return None


def format_email_summary(games_for_date: List[Dict]) -> str:
    lines = [f"NBA Scores Summary for {games_for_date[0]['Day']}:\n"] if games_for_date else ["NBA Scores Summary:\n"]
    for g in games_for_date:
        lines.append(f"{g['AwayTeam']} @ {g['HomeTeam']} - {g['AwayTeamScore']} : {g['HomeTeamScore']}")
    return "\n".join(lines)


def format_email_full(games_for_date: List[Dict]) -> str:
    # Return simple HTML listing of all games with details
    html = [f"<h1>NBA Scores for {games_for_date[0]['Day']}</h1><ul>"] if games_for_date else ["<h1>NBA Scores</h1><ul>"]
    for g in games_for_date:
        html.append(
            f"<li><b>{g['AwayTeam']} @ {g['HomeTeam']}</b>: {g['AwayTeamScore']} - {g['HomeTeamScore']}<br>"
            f"Status: {g.get('Status', 'N/A')}, Quarter: {g.get('Quarter', 'N/A')}, Time Remaining: {g.get('TimeRemaining', 'N/A')}</li>"
        )
    html.append("</ul>")
    return "".join(html)


async def send_email(email: str, subject: str, body: str, html: bool = False):
    # TODO: Implement real email sending using SMTP or email service provider
    # For prototype, just log the email
    logger.info(f"Sending {'HTML' if html else 'plain text'} email to {email}:\nSubject: {subject}\n{body}")


async def process_fetch_and_notify(date: str):
    logger.info(f"Starting fetch and notify for date {date}")
    scores = await fetch_nba_scores(date)
    if scores is None:
        logger.error(f"Failed to fetch data for {date}, aborting notification.")
        return

    # Save to local "db"
    games[date] = scores

    # Notify subscribers asynchronously (fire and forget)
    for email, notif_type in subscribers.items():
        if notif_type == "summary":
            body = format_email_summary(scores)
            await send_email(email, f"NBA Scores Summary for {date}", body, html=False)
        else:  # full
            body = format_email_full(scores)
            await send_email(email, f"NBA Scores Full Listing for {date}", body, html=True)

    logger.info(f"Completed fetch and notify for date {date}")


@app.route("/subscribe", methods=["POST"])
async def subscribe():
    data = await request.get_json(force=True)
    email = data.get("email")
    notification_type = data.get("notificationType", "summary").lower()
    if not email or notification_type not in ("summary", "full"):
        return jsonify({"error": "Invalid email or notificationType"}), 400

    subscribers[email] = notification_type
    logger.info(f"Subscribed/Updated: {email} with notificationType={notification_type}")
    return jsonify({"message": "Subscription added/updated successfully"}), 200


@app.route("/subscribe", methods=["DELETE"])
async def unsubscribe():
    data = await request.get_json(force=True)
    email = data.get("email")
    if not email:
        return jsonify({"error": "Email is required"}), 400
    if email in subscribers:
        del subscribers[email]
        logger.info(f"Unsubscribed: {email}")
        return jsonify({"message": "Subscription removed successfully"}), 200
    else:
        return jsonify({"error": "Email not found"}), 404


@app.route("/subscribers", methods=["GET"])
async def get_subscribers():
    # Return list of subscribers with preferences
    result = [{"email": email, "notificationType": notif} for email, notif in subscribers.items()]
    return jsonify(result), 200


@app.route("/games/fetch", methods=["POST"])
async def fetch_scores():
    data = await request.get_json(force=True)
    date = data.get("date")
    if not date:
        return jsonify({"error": "Date is required in format YYYY-MM-DD"}), 400
    try:
        # Validate date format
        datetime.datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        return jsonify({"error": "Invalid date format. Use YYYY-MM-DD"}), 400

    # Fire and forget the processing task
    asyncio.create_task(process_fetch_and_notify(date))

    return jsonify({"message": "Scores fetch started, notifications will be sent"}), 202


@app.route("/games/all", methods=["GET"])
async def get_all_games():
    try:
        offset = int(request.args.get("offset", 0))
        pagesize = int(request.args.get("pagesize", 20))
    except ValueError:
        return jsonify({"error": "Invalid offset or pagesize parameter"}), 400

    # Flatten all games by date sorted descending
    all_games = []
    for date_key in sorted(games.keys(), reverse=True):
        all_games.extend(games[date_key])

    total = len(all_games)
    paged_games = all_games[offset : offset + pagesize]

    return jsonify({
        "total": total,
        "offset": offset,
        "pagesize": pagesize,
        "games": paged_games
    }), 200


@app.route("/games/<date>", methods=["GET"])
async def get_games_by_date(date):
    try:
        datetime.datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        return jsonify({"error": "Invalid date format. Use YYYY-MM-DD"}), 400

    result = games.get(date, [])
    return jsonify(result), 200


if __name__ == "__main__":
    import logging

    logging.basicConfig(level=logging.INFO)
    app.run(use_reloader=False, debug=True, host="0.0.0.0", port=8000, threaded=True)
```
