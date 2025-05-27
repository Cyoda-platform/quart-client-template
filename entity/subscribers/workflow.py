from typing import Dict
import asyncio
import logging

logger = logging.getLogger(__name__)

async def process_send_welcome_email(entity: Dict):
    email = entity.get("email")
    if email:
        subject = "Welcome to NBA Scores!"
        content = f"Hi {email}, thanks for subscribing to NBA daily scores notifications!"
        try:
            await send_email_mock(email, subject, content)
        except Exception as e:
            logger.exception(f"Failed to send welcome email to {email}: {e}")

async def process_fetch_games(entity: Dict):
    try:
        games = await fetch_nba_games()
        stored_games = []
        for g in games:
            stored_games.append({
                "gameId": str(g["id"]),
                "date": g["date"][:10],
                "homeTeam": g["home_team"]["full_name"],
                "awayTeam": g["visitor_team"]["full_name"],
                "homeScore": g["home_team_score"],
                "awayScore": g["visitor_team_score"],
                "status": g["status"].lower(),
            })
        entity["games_cache"] = stored_games
    except Exception as e:
        logger.exception(f"Failed to fetch/store games: {e}")
        entity["games_cache"] = []

async def process_notify_subscribers(entity: Dict):
    games = entity.get("games_cache", [])
    subscribers = entity.get("subscribers", {})
    tasks = []
    for email, sub in subscribers.items():
        pref_teams = sub.get("preferences", {}).get("favoriteTeams", [])
        relevant_games = [
            g for g in games
            if not pref_teams or g["homeTeam"] in pref_teams or g["awayTeam"] in pref_teams
        ]
        if not relevant_games:
            continue
        content_lines = [
            f"{g['awayTeam']} @ {g['homeTeam']} | {g['awayScore']} - {g['homeScore']} | {g['status']}"
            for g in relevant_games
        ]
        content = "\n".join(content_lines)
        subject = f"NBA Daily Scores - {datetime.utcnow().date().isoformat()}"
        tasks.append(send_email_mock(email, subject, content))
    if tasks:
        await asyncio.gather(*tasks)

async def process_subscribers(entity: Dict):
    # Workflow orchestration only
    await process_fetch_games(entity)
    await process_notify_subscribers(entity)
    await process_send_welcome_email(entity)
    return entity