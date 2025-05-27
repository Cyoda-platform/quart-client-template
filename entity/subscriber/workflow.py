from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

async def process_fetch_scores(entity: dict):
    # Business logic: fetch external NBA scores for given date and store in entity
    # entity expected to have 'date' attribute
    date = entity.get("date")
    if not date:
        date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        entity["date"] = date
    # TODO: add actual fetch logic here, mocked for now
    entity["games"] = []  # Placeholder for fetched games list
    entity["status"] = "fetched"
    logger.info(f"Fetched scores for date {date}")
    return entity

async def process_store_scores(entity: dict):
    # Business logic: store fetched games into entity storage
    # entity expected to have 'games' attribute
    # In this prototype, just mark status
    if "games" in entity and entity["games"]:
        entity["status"] = "stored"
        logger.info(f"Stored {len(entity['games'])} games")
    else:
        entity["status"] = "no_games_to_store"
        logger.info("No games to store")
    return entity

async def process_notify_subscribers(entity: dict):
    # Business logic: notify subscribers with stored scores summary
    # entity expected to have 'games' and 'date'
    subscribers = entity.get("subscribers", [])
    if not subscribers:
        entity["notification_status"] = "no_subscribers"
        logger.info("No subscribers to notify")
        return entity
    # Compose summary (mocked)
    date = entity.get("date", "unknown date")
    games = entity.get("games", [])
    summary = f"NBA Scores Summary for {date}: {len(games)} games."
    # TODO: send email logic here, mocked
    entity["notification_status"] = f"notified {len(subscribers)} subscribers"
    logger.info(entity["notification_status"])
    return entity

async def process_subscriber(entity: dict):
    # Workflow orchestration only - no business logic here
    if "created_at" not in entity:
        entity["created_at"] = datetime.now(timezone.utc).isoformat()
    # Sequentially run all business logic steps
    await process_fetch_scores(entity)
    await process_store_scores(entity)
    await process_notify_subscribers(entity)
    return entity