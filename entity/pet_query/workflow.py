from datetime import datetime
import logging
import asyncio
from typing import Dict, Any

logger = logging.getLogger(__name__)

async def process_pet_query(entity_data: Dict[str, Any]) -> None:
    # workflow orchestration only
    try:
        await process_pets_query(entity_data)
        entity_data['result_status'] = 'completed'
    except Exception as e:
        logger.error(f"Error processing pet_query workflow: {e}")
        entity_data['result_status'] = 'failed'
        entity_data['error_message'] = str(e)
    finally:
        entity_data['processed_at'] = datetime.utcnow().isoformat()

async def process_pets_query(entity_data: Dict[str, Any]) -> None:
    filters = {}
    if 'status' in entity_data and entity_data['status'] is not None:
        filters['status'] = entity_data['status']
    if 'category' in entity_data and entity_data['category'] is not None:
        filters['category'] = entity_data['category']
    if 'tags' in entity_data and entity_data['tags'] is not None:
        filters['tags'] = entity_data['tags']

    pets_data = await fetch_pets_from_petstore(filters)
    entity_data['pets'] = pets_data.get('pets', [])

async def process_pet_detail(entity_data: Dict[str, Any]) -> None:
    pet_id = entity_data.get('id')
    if pet_id is None:
        raise ValueError("Pet ID is required in entity data")
    pet_detail = await fetch_pet_detail_from_petstore(pet_id)
    entity_data['pet_detail'] = pet_detail

# Note: fetch_pets_from_petstore and fetch_pet_detail_from_petstore
# should be defined elsewhere to perform actual API calls asynchronously