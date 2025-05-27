import logging
from datetime import datetime
from typing import Dict

logger = logging.getLogger(__name__)

async def process_fetch(entity: Dict) -> None:
    # Business logic to fetch data from external API and store in entity
    # TODO: Implement actual fetch logic here
    entity['fetched_at'] = datetime.utcnow().isoformat() + "Z"
    entity['status'] = 'fetched'
    logger.info(f"Fetched data for entity: {entity}")

async def process_store(entity: Dict) -> None:
    # Business logic to store fetched data
    # TODO: Implement actual store logic here
    entity['stored_at'] = datetime.utcnow().isoformat() + "Z"
    entity['status'] = 'stored'
    logger.info(f"Stored data for entity: {entity}")

async def process_notify(entity: Dict) -> None:
    # Business logic to send notifications to subscribers
    # TODO: Implement actual notification logic here
    entity['notified_at'] = datetime.utcnow().isoformat() + "Z"
    entity['status'] = 'notified'
    logger.info(f"Notification sent for entity: {entity}")

async def process_game(entity: Dict) -> None:
    # Workflow orchestration only
    await process_fetch(entity)
    await process_store(entity)
    await process_notify(entity)
    entity['processed_at'] = datetime.utcnow().isoformat() + "Z"
    logger.debug(f"Processed game entity: {entity}")