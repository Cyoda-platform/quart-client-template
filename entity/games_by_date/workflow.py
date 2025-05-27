from typing import Dict, List
import datetime
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

_subscribers: List[str] = []

async def fetch_scores_from_external_api(date: str) -> List[Dict]:
    API_KEY = "test"
    NBA_API_URL = "https://api.sportsdata.io/v3/nba/scores/json/ScoresBasicFinal/{date}?key=" + API_KEY
    # TODO: Implement actual fetching logic here
    return []

async def send_email_to_subscribers(date: str, games: List[Dict]):
    # TODO: Implement actual email sending here
    pass

async def process_fetch_scores(entity: Dict) -> Dict:
    date = entity.get("date")
    if not date:
        logger.warning("Entity missing 'date' key in fetch_scores")
        return entity
    games = await fetch_scores_from_external_api(date)
    entity['games'] = games
    entity['fetchedAt'] = datetime.datetime.utcnow().isoformat()
    return entity

async def process_store_games(entity: Dict) -> Dict:
    # In prototype, storing is implicit by modifying entity
    entity['storedAt'] = datetime.datetime.utcnow().isoformat()
    return entity

async def process_send_notifications(entity: Dict) -> Dict:
    date = entity.get("date")
    games = entity.get("games", [])
    if _subscribers and games:
        await send_email_to_subscribers(date, games)
    entity['notifiedAt'] = datetime.datetime.utcnow().isoformat()
    return entity

async def process_games_by_date_fetch(entity: Dict) -> Dict:
    # Workflow orchestration only
    entity = await process_fetch_scores(entity)
    entity = await process_store_games(entity)
    entity = await process_send_notifications(entity)
    entity['processedAt'] = datetime.datetime.utcnow().isoformat()
    return entity