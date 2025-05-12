import logging
from datetime import datetime
from typing import Dict

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

async def process_fetch_cats(entity: Dict):
    filters = entity.get("filters", {}) or {}
    try:
        cats = await fetch_live_cat_data(filters)
        # TODO: Persist cats entities here or trigger separate workflow
        entity["fetched_cats"] = cats  # store temporarily for example
    except Exception as e:
        logger.exception(f"Failed to fetch cats: {e}")
        raise

async def process_update_status_completed(entity: Dict):
    entity["status"] = "completed"
    entity["result_count"] = len(entity.get("fetched_cats", []))
    entity["completedAt"] = datetime.utcnow().isoformat()

async def process_update_status_failed(entity: Dict, error: str):
    entity["status"] = "failed"
    entity["error"] = error

async def process_set_requested(entity: Dict):
    entity["status"] = "processing"
    entity["requestedAt"] = datetime.utcnow().isoformat()

async def process_cat_live_data_fetch_request(entity: Dict) -> Dict:
    # Workflow orchestration only
    await process_set_requested(entity)
    try:
        await process_fetch_cats(entity)
        await process_update_status_completed(entity)
    except Exception as e:
        await process_update_status_failed(entity, str(e))
    return entity