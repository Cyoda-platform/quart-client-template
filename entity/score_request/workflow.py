import asyncio
import logging
from datetime import datetime
from typing import Dict, List

import httpx

logger = logging.getLogger(__name__)

async def process_fetch_scores(entity: Dict):
    date = entity.get("date")
    API_KEY = "test"
    NBA_API_URL_TEMPLATE = "https://api.sportsdata.io/v3/nba/scores/json/ScoresBasicFinal/{date}?key=" + API_KEY

    try:
        url = NBA_API_URL_TEMPLATE.format(date=date)
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            games = resp.json()
            if not isinstance(games, list):
                raise ValueError("Unexpected response format: expected list of games")
        entity["fetched_games"] = games
        entity["fetch_error"] = None
    except Exception as e:
        logger.exception(f"Failed to fetch NBA scores for {date}: {e}")
        entity["fetch_error"] = str(e)
        entity["fetched_games"] = []
        entity["fetch_status"] = "failed"

async def process_store_games(entity: Dict, storage):
    date = entity.get("date")
    games = entity.get("fetched_games", [])
    try:
        await storage.store_games(date, games)
        entity["store_error"] = None
    except Exception as e:
        logger.exception(f"Failed to store games locally for {date}: {e}")
        entity["store_error"] = str(e)
        entity["fetch_status"] = "failed"

async def process_get_subscribers(entity: Dict, get_subscribers_list):
    try:
        subscribers = await get_subscribers_list()
        entity["subscribers"] = subscribers
        entity["subscribers_error"] = None
    except Exception as e:
        logger.exception(f"Failed to get subscribers list: {e}")
        entity["subscribers"] = []
        entity["subscribers_error"] = str(e)
        entity["fetch_status"] = "failed"

async def process_send_notifications(entity: Dict, send_email):
    date = entity.get("date")
    subscribers: List[str] = entity.get("subscribers", [])
    games = entity.get("fetched_games", [])
    num_subscribers = len(subscribers)
    if num_subscribers == 0 or not games:
        entity["notifications_sent"] = 0
        return

    summary_html = build_html_summary(date, games)

    async def safe_send(email):
        try:
            await send_email(email, f"NBA Scores for {date}", summary_html)
        except Exception as ex:
            logger.warning(f"Failed to send email to {email}: {ex}")

    await asyncio.gather(*(safe_send(email) for email in subscribers))
    entity["notifications_sent"] = num_subscribers

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

async def process_score_request(entity: Dict, storage, get_subscribers_list, send_email) -> Dict:
    date = entity.get("date")
    if not date or not isinstance(date, str):
        entity["fetch_status"] = "failed"
        entity["error"] = "Missing or invalid 'date' field"
        logger.error("Score request entity missing valid date")
        return entity
    try:
        datetime.strptime(date, "%Y-%m-%d")
    except Exception:
        entity["fetch_status"] = "failed"
        entity["error"] = "Invalid date format, expected YYYY-MM-DD"
        logger.error(f"Score request entity has invalid date format: {date}")
        return entity

    await process_fetch_scores(entity)
    if entity.get("fetch_status") == "failed" or entity.get("fetch_error"):
        return entity

    await process_store_games(entity, storage)
    if entity.get("fetch_status") == "failed" or entity.get("store_error"):
        return entity

    await process_get_subscribers(entity, get_subscribers_list)
    if entity.get("fetch_status") == "failed" or entity.get("subscribers_error"):
        return entity

    await process_send_notifications(entity, send_email)

    entity["games_stored"] = len(entity.get("fetched_games", []))
    entity["fetch_status"] = "success"
    entity["processed_at"] = datetime.utcnow().isoformat() + "Z"
    return entity