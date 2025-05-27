import httpx
import asyncio
import logging

logger = logging.getLogger(__name__)
NBA_API_URL = "https://api.sportsdata.io/v3/nba/scores/json/ScoresBasicFinal/{date}?key=test"

async def process_fetch_scores(entity: dict):
    date = entity.get("date")
    if not date:
        logger.warning("Game entity missing 'date' field")
        entity["games"] = []
        return
    url = NBA_API_URL.format(date=date)
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            scores = resp.json()
    except Exception:
        logger.exception(f"Failed to fetch NBA scores for {date}")
        scores = []
    entity["games"] = scores

async def process_add_raw_scores(entity: dict):
    # TODO: Add raw scores as supplementary entities externally (cannot update this entity)
    # This function does not modify the entity directly
    try:
        await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model=entity_name_nba_scores_raw,
            entity_version=ENTITY_VERSION,
            entity={
                "date": entity.get("date"),
                "raw_data": entity.get("games", []),
            },
            workflow=None
        )
    except Exception:
        logger.exception("Failed to add raw NBA scores entity")

async def process_notify_subscribers(entity: dict):
    async def _notify():
        try:
            subscribers = await list_subscribers_emails()
            if not subscribers:
                logger.info("No subscribers to notify")
                return
            subject = f"NBA Scores for {entity.get('date')}"
            body = build_email_body(entity.get("date"), entity.get("games", []))
            await send_email(subscribers, subject, body)
            logger.info(f"Notified {len(subscribers)} subscribers")
        except Exception:
            logger.exception("Failed to send notification emails")
    asyncio.create_task(_notify())

async def process_game(entity: dict) -> dict:
    # Workflow orchestration only
    await process_fetch_scores(entity)
    await process_add_raw_scores(entity)
    await process_notify_subscribers(entity)
    return entity