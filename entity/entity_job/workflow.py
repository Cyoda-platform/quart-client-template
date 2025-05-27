import asyncio
import logging
from datetime import datetime
from typing import Dict
import httpx

logger = logging.getLogger(__name__)
NBA_API_URL = "https://api.sportsdata.io/v3/nba/scores/json/ScoresBasicFinal/{date}?key=" + "test"

async def process_fetch_games(entity: Dict):
    date = entity.get('date')
    if not date:
        raise ValueError("Missing date field")

    url = NBA_API_URL.format(date=date)
    async with httpx.AsyncClient() as client:
        response = await client.get(url, timeout=10)
        response.raise_for_status()
        games = response.json()
    entity['fetched_games'] = games or []
    return entity

async def process_delete_existing_games(entity: Dict):
    # TODO: implement deletion logic if needed using external services
    # Placeholder: just mark deletion done
    entity['existing_games_deleted'] = True
    return entity

async def process_store_games(entity: Dict):
    # TODO: implement storing logic with external services
    # Placeholder: mark stored count
    games = entity.get('fetched_games', [])
    entity['stored_games_count'] = len(games)
    return entity

async def process_fetch_subscribers(entity: Dict):
    # TODO: implement fetching subscribers from external service
    # Placeholder: empty list
    entity['subscribers'] = []
    return entity

async def process_send_notifications(entity: Dict):
    subscribers = entity.get('subscribers', [])
    games = entity.get('fetched_games', [])
    date = entity.get('date', 'N/A')
    if not subscribers:
        logger.info("No subscribers to notify.")
    else:
        summary_lines = []
        for game in games:
            home = game.get("HomeTeam", "N/A")
            away = game.get("AwayTeam", "N/A")
            home_score = game.get("HomeTeamScore", "N/A")
            away_score = game.get("AwayTeamScore", "N/A")
            summary_lines.append(f"{away} {away_score} @ {home} {home_score}")
        summary = "\n".join(summary_lines)
        for email in subscribers:
            # TODO: replace with real email sending logic
            logger.info(f"Sending NBA scores notification to {email} for {date}:\n{summary}")
    entity['notifications_sent'] = True
    return entity

async def process_entity_job(entity: Dict) -> Dict:
    """
    Workflow orchestration only.
    """
    entity['status'] = "processing"
    entity['startedAt'] = datetime.utcnow().isoformat()

    try:
        await process_fetch_games(entity)
        if not entity.get('fetched_games'):
            entity['status'] = "completed"
            entity['message'] = f"No games found for date {entity.get('date')}"
            entity['completedAt'] = datetime.utcnow().isoformat()
            return entity

        await process_delete_existing_games(entity)
        await process_store_games(entity)
        await process_fetch_subscribers(entity)
        await process_send_notifications(entity)

        entity['status'] = "completed"
        entity['completedAt'] = datetime.utcnow().isoformat()
        entity['message'] = f"Processed {entity.get('stored_games_count', 0)} games for {entity.get('date')}"

    except Exception as e:
        logger.exception(f"Error processing NBA scores job for date {entity.get('date')}: {e}")
        entity['status'] = "failed"
        entity['error'] = str(e)
        entity['completedAt'] = datetime.utcnow().isoformat()

    return entity