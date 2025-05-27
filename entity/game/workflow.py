from typing import Dict
import httpx
import logging

logger = logging.getLogger(__name__)

async def process_fetch_scores(entity: Dict):
    # Business logic: fetch scores and store in entity
    date = entity.get("date")
    if not date:
        entity["status"] = "error"
        entity["error"] = "Missing date"
        return entity

    url = f"https://api.sportsdata.io/v3/nba/scores/json/ScoresBasicFinal/{date}?key=test"
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()
            # Store fetched games in entity
            entity["games"] = data
            entity["status"] = "fetched"
    except Exception as e:
        logger.exception(e)
        entity["status"] = "error"
        entity["error"] = str(e)
    return entity

async def process_notify_subscribers(entity: Dict):
    # Business logic: send notifications to subscribers
    subscribers = entity.get("subscribers", [])
    games = entity.get("games", [])
    if not subscribers:
        entity["notify_status"] = "no_subscribers"
        return entity
    if not games:
        entity["notify_status"] = "no_games"
        return entity
    summary_lines = []
    for game in games:
        home = game.get("HomeTeam", "N/A")
        away = game.get("AwayTeam", "N/A")
        home_score = game.get("HomeTeamScore", "N/A")
        away_score = game.get("AwayTeamScore", "N/A")
        summary_lines.append(f"{away} {away_score} @ {home} {home_score}")
    summary = "\n".join(summary_lines)
    # TODO: Replace with real email sending
    for email in subscribers:
        logger.info(f"Notify {email}:\n{summary}")
    entity["notify_status"] = "sent"
    return entity

async def process_store_scores(entity: Dict):
    # Business logic: store scores locally (in entity itself)
    # For prototype, assume storage is just keeping the data in entity
    entity["store_status"] = "stored"
    return entity

async def process_game(entity: Dict):
    # Workflow orchestration only
    await process_fetch_scores(entity)
    await process_store_scores(entity)
    await process_notify_subscribers(entity)
    return entity