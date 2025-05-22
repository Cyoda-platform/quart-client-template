import logging
from datetime import datetime
from typing import Dict, Any

logger = logging.getLogger(__name__)

async def process_add_personality(entity: Dict[str, Any]) -> None:
    if "personality" not in entity:
        entity["personality"] = "adorable and unique"

async def process_set_processed_at(entity: Dict[str, Any]) -> None:
    entity.setdefault("processed_at", datetime.utcnow().isoformat())

async def process_petstore_pet(entity: Dict[str, Any]) -> Dict[str, Any]:
    logger.info("Processing petstore_pet entity workflow")
    await process_set_processed_at(entity)
    await process_add_personality(entity)
    return entity