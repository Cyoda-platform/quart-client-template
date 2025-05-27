import asyncio
import datetime
import logging
from dataclasses import dataclass
from typing import Dict, List, Optional

import httpx
from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request, validate_querystring

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

@dataclass
class SubscribeRequest:
    email: str
    notificationType: str

@dataclass
class UnsubscribeRequest:
    email: str

@dataclass
class FetchRequest:
    date: str

@dataclass
class PaginationQuery:
    offset: int = 0
    pagesize: int = 20

# --- In-memory "database" ---
subscribers: Dict[str, str] = {}
games: Dict[str, List[Dict]] = {}

API_KEY = "test"
API_URL = "https://api.sportsdata.io/v3/nba/scores/json/ScoresBasicFinal/{date}?key={key}"

async def fetch_nba_scores(date: str) -> Optional[List[Dict]]:
    url = API_URL.format(date=date, key=API_KEY)
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, timeout=20.0)
            resp.raise_for_status()
            return resp.json()
    except httpx.HTTPError as e:
        logger.exception(f"Failed to fetch NBA scores for {date}: {e}")
        return None

def format_email_summary(games_for_date: List[Dict]) -> str:
    lines = [f"NBA Scores Summary for {games_for_date[0]['Day']}:\n"] if games_for_date else ["NBA Scores Summary:\n"]
    for g in games_for_date:
        lines.append(f"{g['AwayTeam']} @ {g['HomeTeam']} - {g['AwayTeamScore']} : {g['HomeTeamScore']}")
    return "\n".join(lines)

def format_email_full(games_for_date: List[Dict]) -> str:
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
    logger.info(f"Sending {'HTML' if html else 'plain text'} email to {email}:\nSubject: {subject}\n{body}")

async def process_fetch_and_notify(date: str):
    logger.info(f"Starting fetch and notify for date {date}")
    scores = await fetch_nba_scores(date)
    if scores is None:
        logger.error(f"Failed to fetch data for {date}, aborting notification.")
        return
    games[date] = scores
    for email, notif_type in subscribers.items():
        if notif_type == "summary":
            body = format_email_summary(scores)
            await send_email(email, f"NBA Scores Summary for {date}", body, html=False)
        else:
            body = format_email_full(scores)
            await send_email(email, f"NBA Scores Full Listing for {date}", body, html=True)
    logger.info(f"Completed fetch and notify for date {date}")

@app.route("/subscribe", methods=["POST"])
@validate_request(SubscribeRequest)  # validation last for POST (workaround for quart-schema issue)
async def subscribe(data: SubscribeRequest):
    if data.notificationType.lower() not in ("summary", "full"):
        return jsonify({"error": "Invalid notificationType"}), 400
    subscribers[data.email] = data.notificationType.lower()
    logger.info(f"Subscribed/Updated: {data.email} with notificationType={data.notificationType}")
    return jsonify({"message": "Subscription added/updated successfully"}), 200

@app.route("/subscribe", methods=["DELETE"])
@validate_request(UnsubscribeRequest)  # validation last for POST/DELETE
async def unsubscribe(data: UnsubscribeRequest):
    if data.email in subscribers:
        del subscribers[data.email]
        logger.info(f"Unsubscribed: {data.email}")
        return jsonify({"message": "Subscription removed successfully"}), 200
    return jsonify({"error": "Email not found"}), 404

@app.route("/subscribers", methods=["GET"])
async def get_subscribers():
    result = [{"email": email, "notificationType": notif} for email, notif in subscribers.items()]
    return jsonify(result), 200

@validate_querystring(PaginationQuery)  # validation first for GET (workaround for quart-schema issue)
@app.route("/games/all", methods=["GET"])
async def get_all_games(query_args: PaginationQuery):
    all_games = []
    for date_key in sorted(games.keys(), reverse=True):
        all_games.extend(games[date_key])
    total = len(all_games)
    paged_games = all_games[query_args.offset: query_args.offset + query_args.pagesize]
    return jsonify({
        "total": total,
        "offset": query_args.offset,
        "pagesize": query_args.pagesize,
        "games": paged_games
    }), 200

@app.route("/games/<date>", methods=["GET"])
async def get_games_by_date(date):
    try:
        datetime.datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        return jsonify({"error": "Invalid date format. Use YYYY-MM-DD"}), 400
    return jsonify(games.get(date, [])), 200

@app.route("/games/fetch", methods=["POST"])
@validate_request(FetchRequest)  # validation last for POST
async def fetch_scores(data: FetchRequest):
    try:
        datetime.datetime.strptime(data.date, "%Y-%m-%d")
    except ValueError:
        return jsonify({"error": "Invalid date format. Use YYYY-MM-DD"}), 400
    asyncio.create_task(process_fetch_and_notify(data.date))
    return jsonify({"message": "Scores fetch started, notifications will be sent"}), 202

if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    app.run(use_reloader=False, debug=True, host="0.0.0.0", port=8000, threaded=True)