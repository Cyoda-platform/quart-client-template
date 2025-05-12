import logging
from datetime import datetime
from typing import Dict

logger = logging.getLogger(__name__)

async def process_fetch_facts(entity: Dict):
    filters = entity.get("filters", {})
    data = await fetch_cat_facts(filters)
    entity["result"] = data

async def process_fetch_breeds(entity: Dict):
    filters = entity.get("filters", {})
    data = await fetch_cat_breeds(filters)
    entity["result"] = data

async def process_fetch_images(entity: Dict):
    filters = entity.get("filters", {})
    data = await fetch_cat_images(filters)
    entity["result"] = data

async def process_fetch_random(entity: Dict):
    filters = entity.get("filters", {})
    facts = await fetch_cat_facts(filters)
    images = await fetch_cat_images(filters)
    breeds = await fetch_cat_breeds(filters)
    data = {
        "facts": facts[:3],
        "images": images[:3],
        "breeds": breeds[:3],
    }
    entity["result"] = data

async def process_entity_job(entity: Dict) -> Dict:
    try:
        entity["status"] = "processing"
        data_type = entity.get("data_type")

        if data_type == "facts":
            await process_fetch_facts(entity)
        elif data_type == "breeds":
            await process_fetch_breeds(entity)
        elif data_type == "images":
            await process_fetch_images(entity)
        elif data_type == "random":
            await process_fetch_random(entity)
        else:
            entity["result"] = []

        entity["processed_at"] = datetime.utcnow().isoformat()
        entity["status"] = "done"
        entity["workflow_processed_at"] = datetime.utcnow().isoformat()

    except Exception as e:
        logger.exception(e)
        entity["status"] = "error"
        entity["error"] = str(e)

    return entity