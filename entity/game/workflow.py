import logging
import asyncio
from typing import Dict, List
import httpx

logger = logging.getLogger(__name__)
NBA_API_URL = "https://api.sportsdata.io/v3/nba/scores/json/ScoresBasicFinal/{date}?key={key}"
API_KEY = "test"

async def process_game(entity: Dict) -> Dict:
    # Workflow orchestration only: call processing steps in order
    await process_fetch_scores(entity)
    await process_persist_game_details(entity)
    await process_notify_subscribers(entity)
    return entity

async def process_fetch_scores(entity: Dict):
    fetch_date = entity.get("date")
    if not fetch_date:
        logger.warning("Game entity missing 'date' field; skipping fetch.")
        entity["fetch_status"] = "error: missing date field"
        return

    try:
        async with httpx.AsyncClient() as client:
            url = NBA_API_URL.format(date=fetch_date, key=API_KEY)
            resp = await client.get(url, timeout=10)
            resp.raise_for_status()
            games_data = resp.json()
            if not isinstance(games_data, list):
                logger.warning(f"Unexpected data format from NBA API for date {fetch_date}")
                games_data = []
            entity["games_data"] = games_data  # store fetched games in entity for later steps
            entity["fetch_status"] = "success"
            entity["games_count"] = len(games_data)
            logger.info(f"Fetched {len(games_data)} games for date {fetch_date}")
    except Exception as e:
        logger.error(f"Failed to fetch NBA scores for {fetch_date}: {e}")
        entity["fetch_status"] = f"error: {str(e)}"
        entity["games_data"] = []

async def process_persist_game_details(entity: Dict):
    # TODO: Replace with actual persistence logic
    # Using entity["games_data"] populated by fetch_scores
    games_data = entity.get("games_data", [])
    fetch_date = entity.get("date")
    if not fetch_date:
        logger.warning("No date found in entity for persistence step.")
        return
    try:
        # Simulate persistence by storing in entity, or call to external service
        entity["persisted_game_details"] = True
        logger.info(f"Persisted game details for {fetch_date}")
    except Exception as e:
        logger.error(f"Failed to persist game details for {fetch_date}: {e}")

async def process_notify_subscribers(entity: Dict):
    games_data = entity.get("games_data", [])
    fetch_date = entity.get("date")
    if not fetch_date:
        logger.warning("No date found in entity for notification step.")
        return

    # TODO: Replace with actual subscriber retrieval
    subscribers = entity.get("subscribers", [])  # Expect subscribers list injected in entity or fetched externally

    emails = [sub.get("email") for sub in subscribers if "email" in sub]

    def format_scores_summary(games: List[Dict]) -> str:
        if not games:
            return "No games found for this date."
        lines = []
        for g in games:
            away = g.get('AwayTeam', 'N/A')
            home = g.get('HomeTeam', 'N/A')
            away_score = g.get('AwayTeamScore', 'N/A')
            home_score = g.get('HomeTeamScore', 'N/A')
            status = g.get('Status', 'N/A')
            lines.append(f"{away} @ {home}: {away_score} - {home_score} ({status})")
        return "\n".join(lines)

    summary = format_scores_summary(games_data)
    subject = f"NBA Scores for {fetch_date}"

    async def send_email(to_emails: List[str], subject: str, body: str):
        # Placeholder for actual email sending implementation
        logger.info(f"Sending email to {len(to_emails)} subscribers:\nSubject: {subject}\nBody:\n{body}")

    if emails:
        asyncio.create_task(send_email(emails, subject, summary))
        entity["notified_subscribers"] = len(emails)
        logger.info(f"Email notification task started for {len(emails)} subscribers")
    else:
        entity["notified_subscribers"] = 0
        logger.info("No subscribers to notify.")