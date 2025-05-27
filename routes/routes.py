import asyncio
import datetime
import logging
from dataclasses import dataclass
from typing import List, Optional

import httpx
from quart import Quart, jsonify
from quart_schema import QuartSchema, validate_request, validate_querystring

from app_init.app_init import BeanFactory
from common.config.config import ENTITY_VERSION

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

factory = BeanFactory(config={'CHAT_REPOSITORY': 'cyoda'})
entity_service = factory.get_services()['entity_service']
cyoda_auth_service = factory.get_services()["cyoda_auth_service"]

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
    api_key: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None

@dataclass
class PaginationQuery:
    offset: int = 0
    pagesize: int = 20

ENTITY_NAME = "subscribe_request"
GAMES_ENTITY_NAME = "game"
FETCH_REQUEST_ENTITY_NAME = "fetch_request"

API_URL = "https://api.sportsdata.io/v3/nba/scores/json/ScoresBasicFinal/{date}?key={key}"

async def fetch_nba_scores(date: str, api_key: str) -> Optional[List[dict]]:
    url = API_URL.format(date=date, key=api_key)
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, timeout=20.0)
            resp.raise_for_status()
            return resp.json()
    except httpx.HTTPError as e:
        logger.exception(f"Failed to fetch NBA scores for {date}: {e}")
        return None

def format_email_summary(games_for_date: List[dict]) -> str:
    lines = [f"NBA Scores Summary for {games_for_date[0]['Day']}:\n"] if games_for_date else ["NBA Scores Summary:\n"]
    for g in games_for_date:
        lines.append(f"{g['AwayTeam']} @ {g['HomeTeam']} - {g['AwayTeamScore']} : {g['HomeTeamScore']}")
    return "\n".join(lines)

def format_email_full(games_for_date: List[dict]) -> str:
    html = [f"<h1>NBA Scores for {games_for_date[0]['Day']}</h1><ul>"] if games_for_date else ["<h1>NBA Scores</h1><ul>"]
    for g in games_for_date:
        html.append(
            f"<li><b>{g['AwayTeam']} @ {g['HomeTeam']}</b>: {g['AwayTeamScore']} - {g['HomeTeamScore']}<br>"
            f"Status: {g.get('Status', 'N/A')}, Quarter: {g.get('Quarter', 'N/A')}, Time Remaining: {g.get('TimeRemaining', 'N/A')}</li>"
        )
    html.append("</ul>")
    return "".join(html)

async def send_email(email: str, subject: str, body: str, html: bool = False):
    # TODO: Implement real email sending via SMTP or email service provider
    logger.info(f"Sending {'HTML' if html else 'plain text'} email to {email}:\nSubject: {subject}\n{body}")

async def process_subscribe_request(entity: dict) -> dict:
    logger.info(f"Running workflow on subscribe_request entity: {entity}")
    entity["processed_at"] = datetime.datetime.utcnow().isoformat()
    return entity

async def process_fetch_request(entity: dict) -> dict:
    logger.info(f"Running workflow on fetch_request entity: {entity}")

    api_key = entity.get("api_key")
    start_date_str = entity.get("start_date")
    end_date_str = entity.get("end_date")

    try:
        if start_date_str:
            start_dt = datetime.datetime.strptime(start_date_str, "%Y-%m-%d")
        else:
            start_dt = datetime.datetime.strptime(end_date_str, "%Y-%m-%d") if end_date_str else datetime.datetime.utcnow()

        if end_date_str:
            end_dt = datetime.datetime.strptime(end_date_str, "%Y-%m-%d")
        else:
            end_dt = start_dt

        if start_dt > end_dt:
            logger.warning("start_date is after end_date; swapping")
            start_dt, end_dt = end_dt, start_dt
    except Exception as e:
        logger.error(f"Invalid date format in fetch_request: {e}")
        return entity

    current_date = start_dt
    while current_date <= end_dt:
        date_str = current_date.strftime("%Y-%m-%d")
        logger.info(f"Fetching NBA scores for date: {date_str}")
        scores = await fetch_nba_scores(date_str, api_key)
        if scores is None:
            logger.error(f"Failed to fetch scores for {date_str}, skipping")
            current_date += datetime.timedelta(days=1)
            continue

        try:
            await entity_service.add_item(
                token=cyoda_auth_service,
                entity_model=GAMES_ENTITY_NAME,
                entity_version=ENTITY_VERSION,
                entity={"date": date_str, "scores": scores},
                workflow=None
            )
            logger.info(f"Saved games for {date_str}")
        except Exception as e:
            logger.exception(f"Failed to save games for {date_str}: {e}")

        try:
            subscribers_list = await entity_service.get_items(
                token=cyoda_auth_service,
                entity_model=ENTITY_NAME,
                entity_version=ENTITY_VERSION,
            )
        except Exception as e:
            logger.exception(f"Failed to get subscribers: {e}")
            subscribers_list = []

        for subscriber in subscribers_list:
            email = subscriber.get("email")
            notif_type = subscriber.get("notificationtype")
            if not email or not notif_type:
                continue
            try:
                if notif_type == "summary":
                    body = format_email_summary(scores)
                    await send_email(email, f"NBA Scores Summary for {date_str}", body, html=False)
                else:
                    body = format_email_full(scores)
                    await send_email(email, f"NBA Scores Full Listing for {date_str}", body, html=True)
            except Exception as e:
                logger.exception(f"Failed to send email to {email}: {e}")

        current_date += datetime.timedelta(days=1)

    entity["processed_at"] = datetime.datetime.utcnow().isoformat()
    entity["status"] = "completed"
    return entity

@app.route("/subscribe", methods=["POST"])
@validate_request(SubscribeRequest)
async def subscribe(data: SubscribeRequest):
    if data.notificationType.lower() not in ("summary", "full"):
        return jsonify({"error": "Invalid notificationType"}), 400
    entity_data = {
        "email": data.email,
        "notificationtype": data.notificationType.lower()
    }
    try:
        id = await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model=ENTITY_NAME,
            entity_version=ENTITY_VERSION,
            entity=entity_data
        )
        return jsonify({"id": str(id)}), 200
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to add subscription"}), 500

@app.route("/subscribe", methods=["DELETE"])
@validate_request(UnsubscribeRequest)
async def unsubscribe(data: UnsubscribeRequest):
    try:
        subscribers_list = await entity_service.get_items(
            token=cyoda_auth_service,
            entity_model=ENTITY_NAME,
            entity_version=ENTITY_VERSION
        )
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to get subscribers"}), 500

    technical_id = None
    for item in subscribers_list:
        if item.get("email") == data.email:
            technical_id = item.get("id") or item.get("technical_id")
            break

    if not technical_id:
        return jsonify({"error": "Email not found"}), 404

    try:
        await entity_service.delete_item(
            token=cyoda_auth_service,
            entity_model=ENTITY_NAME,
            entity_version=ENTITY_VERSION,
            technical_id=str(technical_id),
            meta={}
        )
        logger.info(f"Unsubscribed: {data.email}")
        return jsonify({"message": "Subscription removed successfully"}), 200
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to remove subscription"}), 500

@app.route("/subscribers", methods=["GET"])
async def get_subscribers():
    try:
        subscribers_list = await entity_service.get_items(
            token=cyoda_auth_service,
            entity_model=ENTITY_NAME,
            entity_version=ENTITY_VERSION,
        )
        result = []
        for s in subscribers_list:
            email = s.get("email")
            notif = s.get("notificationtype")
            if email and notif:
                result.append({"email": email, "notificationType": notif})
        return jsonify(result), 200
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to retrieve subscribers"}), 500

@validate_querystring(PaginationQuery)
@app.route("/games/all", methods=["GET"])
async def get_all_games(query_args: PaginationQuery):
    try:
        all_games_raw = await entity_service.get_items(
            token=cyoda_auth_service,
            entity_model=GAMES_ENTITY_NAME,
            entity_version=ENTITY_VERSION,
        )
        all_games = []
        for entry in all_games_raw:
            scores = entry.get("scores", [])
            all_games.extend(scores)
        total = len(all_games)
        paged_games = all_games[query_args.offset: query_args.offset + query_args.pagesize]
        return jsonify({
            "total": total,
            "offset": query_args.offset,
            "pagesize": query_args.pagesize,
            "games": paged_games
        }), 200
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to retrieve games"}), 500

@app.route("/games/<date>", methods=["GET"])
async def get_games_by_date(date):
    try:
        datetime.datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        return jsonify({"error": "Invalid date format. Use YYYY-MM-DD"}), 400

    condition = {
        "cyoda": {
            "type": "group",
            "operator": "AND",
            "conditions": [
                {
                    "jsonPath": "$.date",
                    "operatorType": "EQUALS",
                    "value": date,
                    "type": "simple"
                }
            ]
        }
    }
    try:
        items = await entity_service.get_items_by_condition(
            token=cyoda_auth_service,
            entity_model=GAMES_ENTITY_NAME,
            entity_version=ENTITY_VERSION,
            condition=condition
        )
        if not items:
            return jsonify([]), 200
        scores = items[0].get("scores", [])
        return jsonify(scores), 200
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to retrieve games for date"}), 500

@app.route("/games/fetch", methods=["POST"])
@validate_request(FetchRequest)
async def fetch_scores(data: FetchRequest):
    entity_data = {
        "api_key": data.api_key,
        "start_date": data.start_date,
        "end_date": data.end_date,
    }
    try:
        await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model=FETCH_REQUEST_ENTITY_NAME,
            entity_version=ENTITY_VERSION,
            entity=entity_data
        )
        return jsonify({"message": "Scores fetch started, notifications will be sent"}), 202
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to start fetch process"}), 500

if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    app.run(use_reloader=False, debug=True, host="0.0.0.0", port=8000, threaded=True)