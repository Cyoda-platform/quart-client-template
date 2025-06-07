import asyncio
import datetime
import logging
from dataclasses import dataclass
from typing import Dict, List, Optional

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request, validate_querystring

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# Request/Query models
@dataclass
class SubscribeRequest:
    email: str
    notificationType: str

@dataclass
class UnsubscribeRequest:
    email: str

@dataclass
class FetchRequest:
    api_key: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None

@dataclass
class PaginationQuery:
    offset: int = 0
    pagesize: int = 20

# In-memory "persistence" for prototype
class Storage:
    def __init__(self):
        self.subscribers: Dict[str, Dict] = {}
        self.game_data: Dict[str, List[Dict]] = {}

storage = Storage()

API_URL = "https://api.sportsdata.io/v3/nba/scores/json/ScoresBasicFinal/{date}?key={key}"

async def fetch_nba_scores(date: str, api_key: str) -> Optional[List[Dict]]:
    url = API_URL.format(date=date, key=api_key)
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, timeout=20.0)
            resp.raise_for_status()
            return resp.json()
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error occurred: {e.response.status_code} - {e.response.text}")
        return None
    except Exception as e:
        logger.exception(f"Failed to fetch NBA scores for {date}: {e}")
        return None

def format_email_summary(games_for_date: List[Dict]) -> str:
    if not games_for_date:
        return "NBA Scores Summary: No games found for this date."
    
    lines = [f"NBA Scores Summary for {games_for_date[0].get('Day', 'Unknown Date')}:"]
    for g in games_for_date:
        lines.append(f"{g.get('AwayTeam', 'Away')} @ {g.get('HomeTeam', 'Home')} - {g.get('AwayTeamScore', 0)} : {g.get('HomeTeamScore', 0)}")
    return "\n".join(lines)

def format_email_full(games_for_date: List[Dict]) -> str:
    if not games_for_date:
        return "<h1>NBA Scores</h1><p>No games found for this date.</p>"
    
    html = [f"<h1>NBA Scores for {games_for_date[0].get('Day', 'Unknown Date')}</h1><ul>"]
    for g in games_for_date:
        html.append(
            f"<li><b>{g.get('AwayTeam', 'Away')} @ {g.get('HomeTeam', 'Home')}</b>: {g.get('AwayTeamScore', 0)} - {g.get('HomeTeamScore', 0)}<br>"
            f"Status: {g.get('Status', 'N/A')}, Quarter: {g.get('Quarter', 'N/A')}, Time Remaining: {g.get('TimeRemaining', 'N/A')}</li>"
        )
    html.append("</ul>")
    return "".join(html)

async def send_email(email: str, subject: str, body: str, html: bool = False):
    # TODO: Implement real email sending using SMTP or email service provider
    logger.info(f"Sending {'HTML' if html else 'plain text'} email to {email}:\nSubject: {subject}\n{body}")

async def process_fetch_and_notify_for_date(date: str, api_key: str):
    logger.info(f"Starting fetch and notify for date {date}")
    scores = await fetch_nba_scores(date, api_key)
    if scores is None:
        logger.error(f"Failed to fetch data for {date}, aborting notification.")
        return
    
    storage.game_data[date] = scores
    
    for email, sub_info in storage.subscribers.items():
        notif_type = sub_info.get("notificationType", "summary")
        if notif_type == "summary":
            body = format_email_summary(scores)
            await send_email(email, f"NBA Scores Summary for {date}", body, html=False)
        else:
            body = format_email_full(scores)
            await send_email(email, f"NBA Scores Full Listing for {date}", body, html=True)
    
    logger.info(f"Completed fetch and notify for date {date}")

async def process_fetch_and_notify(data: FetchRequest):
    try:
        if data.start_date:
            try:
                start_dt = datetime.datetime.strptime(data.start_date, "%Y-%m-%d")
            except ValueError:
                logger.error(f"Invalid start_date format: {data.start_date}")
                return
        else:
            start_dt = None

        if data.end_date:
            try:
                end_dt = datetime.datetime.strptime(data.end_date, "%Y-%m-%d")
            except ValueError:
                logger.error(f"Invalid end_date format: {data.end_date}")
                return
        else:
            end_dt = None

        if start_dt is None and end_dt is None:
            logger.error("No valid date provided for fetching.")
            return

        if start_dt is None:
            start_dt = end_dt
        elif end_dt is None:
            end_dt = start_dt

        if start_dt > end_dt:
            logger.error("start_date must be before or equal to end_date.")
            return

        current_date = start_dt
        tasks = []
        while current_date <= end_dt:
            date_str = current_date.strftime("%Y-%m-%d")
            tasks.append(process_fetch_and_notify_for_date(date_str, data.api_key))
            current_date += datetime.timedelta(days=1)

        await asyncio.gather(*tasks)
    except Exception as e:
        logger.exception(f"Exception during fetch and notify: {e}")

@app.route("/subscribe", methods=["POST"])
@validate_request(SubscribeRequest)
async def subscribe(data: SubscribeRequest):
    try:
        if data.notificationType.lower() not in ("summary", "full"):
            return jsonify({"error": "Invalid notificationType"}), 400
        
        storage.subscribers[data.email] = {"notificationType": data.notificationType.lower()}
        logger.info(f"Subscribed/Updated: {data.email} with notificationType={data.notificationType}")
        return jsonify({"message": "Subscription added/updated successfully"}), 200
    except Exception as e:
        logger.exception(f"Error in subscribe endpoint: {e}")
        return jsonify({"error": "Internal server error"}), 500

@app.route("/subscribe", methods=["DELETE"])
@validate_request(UnsubscribeRequest)
async def unsubscribe(data: UnsubscribeRequest):
    try:
        if data.email in storage.subscribers:
            del storage.subscribers[data.email]
            logger.info(f"Unsubscribed: {data.email}")
            return jsonify({"message": "Subscription removed successfully"}), 200
        return jsonify({"error": "Email not found"}), 404
    except Exception as e:
        logger.exception(f"Error in unsubscribe endpoint: {e}")
        return jsonify({"error": "Internal server error"}), 500

@app.route("/subscribers", methods=["GET"])
async def get_subscribers():
    try:
        result = [
            {"email": email, "notificationType": sub_info.get("notificationType", "summary")} 
            for email, sub_info in storage.subscribers.items()
        ]
        return jsonify(result), 200
    except Exception as e:
        logger.exception(f"Error in get_subscribers endpoint: {e}")
        return jsonify({"error": "Internal server error"}), 500

@app.route("/games/all", methods=["GET"])
@validate_querystring(PaginationQuery)
async def get_all_games(query_args: PaginationQuery):
    try:
        all_games = []
        for date_key in sorted(storage.game_data.keys(), reverse=True):
            all_games.extend(storage.game_data[date_key])
        
        total = len(all_games)
        paged_games = all_games[query_args.offset: query_args.offset + query_args.pagesize]
        
        return jsonify({
            "total": total,
            "offset": query_args.offset,
            "pagesize": query_args.pagesize,
            "games": paged_games
        }), 200
    except Exception as e:
        logger.exception(f"Error in get_all_games endpoint: {e}")
        return jsonify({"error": "Internal server error"}), 500

@app.route("/games/<date>", methods=["GET"])
async def get_games_by_date(date):
    try:
        try:
            datetime.datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            return jsonify({"error": "Invalid date format. Use YYYY-MM-DD"}), 400
        
        return jsonify(storage.game_data.get(date, [])), 200
    except Exception as e:
        logger.exception(f"Error in get_games_by_date endpoint: {e}")
        return jsonify({"error": "Internal server error"}), 500

@app.route("/games/fetch", methods=["POST"])
@validate_request(FetchRequest)
async def fetch_scores(data: FetchRequest):
    try:
        # Validate date formats and range
        if data.start_date:
            try:
                datetime.datetime.strptime(data.start_date, "%Y-%m-%d")
            except ValueError:
                return jsonify({"error": "Invalid start_date format. Use YYYY-MM-DD"}), 400
        
        if data.end_date:
            try:
                datetime.datetime.strptime(data.end_date, "%Y-%m-%d")
            except ValueError:
                return jsonify({"error": "Invalid end_date format. Use YYYY-MM-DD"}), 400
        
        if not data.start_date and not data.end_date:
            return jsonify({"error": "At least one of start_date or end_date must be provided"}), 400
        
        if not data.api_key:
            return jsonify({"error": "API key is required"}), 400

        # Create a background task to process the request
        asyncio.create_task(process_fetch_and_notify(data))
        return jsonify({"message": "Scores fetch started, notifications will be sent"}), 202
    except Exception as e:
        logger.exception(f"Error in fetch_scores endpoint: {e}")
        return jsonify({"error": "Internal server error"}), 500

if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO, stream=sys.stdout,
                        format="%(asctime)s %(levelname)s %(name)s - %(message)s")
    app.run(use_reloader=False, debug=True, host="0.0.0.0", port=8000, threaded=True)
