import asyncio
import datetime
import logging
from typing import List, Optional
import httpx
from quart import Quart, jsonify
from quart_schema import QuartSchema, validate_request, validate_querystring

logger = logging.getLogger(__name__)

async def fetch_nba_scores(date: str, api_key: str) -> Optional[List[dict]]:
    url = f"https://api.sportsdata.io/v3/nba/scores/json/ScoresBasicFinal/{date}?key={api_key}"
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, timeout=20.0)
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
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
    # TODO: implement actual email sending
    logger.info(f"Sending {'HTML' if html else 'plain text'} email to {email}:\nSubject: {subject}\n{body}")

async def process_save_scores(entity: dict, date_str: str, scores: List[dict]):
    # Save fetched scores inside entity state under "saved_scores" dict keyed by date
    if "saved_scores" not in entity:
        entity["saved_scores"] = {}
    entity["saved_scores"][date_str] = scores
    logger.info(f"Scores saved in entity for date {date_str}")

async def process_notify_subscribers(entity: dict, date_str: str, scores: List[dict]):
    subscribers_list = entity.get("subscribers", [])
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
        entity["status"] = "error"
        entity["error"] = f"Invalid date format: {e}"
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

        await process_save_scores(entity, date_str, scores)
        await process_notify_subscribers(entity, date_str, scores)

        current_date += datetime.timedelta(days=1)

    entity["processed_at"] = datetime.datetime.utcnow().isoformat()
    entity["status"] = "completed"
    return entity