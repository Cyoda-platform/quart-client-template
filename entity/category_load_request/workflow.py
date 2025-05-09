import logging
from typing import Dict, Any
from datetime import datetime
import httpx

ENTITY_NAME = "category"
LOAD_REQUEST_ENTITY_NAME = "category_load_request"
EXTERNAL_API_URL = "https://api.practicesoftwaretesting.com/categories/tree"

logger = logging.getLogger(__name__)

async def fetch_external_category_tree() -> Dict[str, Any]:
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(EXTERNAL_API_URL, timeout=10)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.exception(f"Failed to fetch external category tree: {e}")
            raise

def transform_to_hierarchy(raw_data: Any) -> Dict[str, Any]:
    # Placeholder for actual transformation logic if needed
    return raw_data

async def process_fetch_and_transform(entity_data: Dict[str, Any]):
    try:
        raw_tree = await fetch_external_category_tree()
        transformed_tree = transform_to_hierarchy(raw_tree)
        entity_data['transformedTree'] = transformed_tree
    except Exception as e:
        logger.error(f"Error in fetch and transform: {e}")
        entity_data['error'] = str(e)
        entity_data['status'] = 'error'

async def process_persist_category_tree(entity_data: Dict[str, Any]):
    if entity_data.get('status') == 'error':
        return
    try:
        # TODO: Replace with actual persistence call
        # await entity_service.add_item(
        #     token=cyoda_auth_service,
        #     entity_model=ENTITY_NAME,
        #     entity_version=ENTITY_VERSION,
        #     entity=entity_data['transformedTree'],
        #     workflow=process_category
        # )
        pass
    except Exception as e:
        logger.error(f"Error persisting category tree: {e}")
        entity_data['error'] = str(e)
        entity_data['status'] = 'error'

def process_update_status_loaded(entity_data: Dict[str, Any]):
    if entity_data.get('status') != 'error':
        entity_data['status'] = 'loaded'
        entity_data['loadedAt'] = datetime.utcnow().isoformat()