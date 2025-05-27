import logging
from typing import Dict

logger = logging.getLogger(__name__)

async def process_subscriber(entity: Dict) -> Dict:
    # Workflow orchestration: sequence of processing steps
    await process_set_subscribed_at(entity)
    await process_other_subscriber_logic(entity)
    return entity

async def process_set_subscribed_at(entity: Dict):
    import datetime
    if "subscribed_at" not in entity:
        entity["subscribed_at"] = datetime.datetime.utcnow().isoformat()

async def process_other_subscriber_logic(entity: Dict):
    # Placeholder for additional subscriber-related business logic
    pass