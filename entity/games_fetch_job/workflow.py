from typing import Dict
import asyncio
import logging
from datetime import datetime
import httpx

logger = logging.getLogger(__name__)
NBA_API_BASE = "https://www.balldontlie.io/api/v1"

async def process_games_fetch_job(entity: Dict) -> Dict:
    # Workflow orchestration only
    logger.info("Starting games fetch job workflow")
    try:
        await process_fetch_games(entity)
        await process_add_games(entity)
        await process_notify_subscribers(entity)
        entity["status"] = "completed"
        entity["completedAt"] = datetime.utcnow().isoformat()
    except Exception as e:
        logger.exception(f"Error in process_games_fetch_job workflow: {e}")
        entity["status"] = "failed"
        entity["error"] = str(e)
    return entity

async def process_fetch_games(entity: Dict):
    today = datetime.utcnow().date().isoformat()
    url = f"{NBA_API_BASE}/games"
    params = {"dates[]": today, "per_page": 100}
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        games = data.get("data", [])
        logger.info(f"Fetched {len(games)} games for {today}")
        entity["fetched_games"] = games
        entity["fetch_date"] = today

async def process_add_games(entity: Dict):
    games = entity.get("fetched_games", [])
    stored_games = []
    for g in games:
        game_entity = {
            "gameId": str(g["id"]),
            "date": g["date"][:10],
            "homeTeam": g["home_team"]["full_name"],
            "awayTeam": g["visitor_team"]["full_name"],
            "homeScore": g["home_team_score"],
            "awayScore": g["visitor_team_score"],
            "status": g["status"].lower(),
        }
        # Instead of adding via entity_service, store locally in entity
        stored_games.append(game_entity)
    entity["stored_games"] = stored_games
    logger.info(f"Processed {len(stored_games)} games to stored_games")

async def process_notify_subscribers(entity: Dict):
    # TODO: Replace with real subscriber fetching logic
    subscribers = entity.get("subscribers", [])
    stored_games = entity.get("stored_games", [])
    today = entity.get("fetch_date", datetime.utcnow().date().isoformat())

    async def notify(sub: Dict):
        email = sub.get("email")
        if not email:
            return
        pref_teams = sub.get("preferences", {}).get("favoriteTeams", [])
        relevant_games = [
            g for g in stored_games
            if not pref_teams or g["homeTeam"] in pref_teams or g["awayTeam"] in pref_teams
        ]
        if not relevant_games:
            return
        content_lines = [
            f"{g['awayTeam']} @ {g['homeTeam']} | {g['awayScore']} - {g['homeScore']} | {g['status']}"
            for g in relevant_games
        ]
        content = "\n".join(content_lines)
        subject = f"NBA Daily Scores - {today}"
        try:
            await send_email_mock(email, subject, content)
        except Exception as e:
            logger.exception(f"Failed to send email to {email}: {e}")

    await asyncio.gather(*(notify(sub) for sub in subscribers), return_exceptions=True)
    logger.info(f"Sent notifications to {len(subscribers)} subscribers")

async def send_email_mock(email: str, subject: str, content: str):
    logger.info(f"Sending email to {email} with subject '{subject}'")
    await asyncio.sleep(0.1)  # TODO: Replace with real email sending logic