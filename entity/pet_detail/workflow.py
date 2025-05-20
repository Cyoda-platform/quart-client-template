from datetime import datetime
import logging
import asyncio
from typing import Dict, Any

logger = logging.getLogger(__name__)

async def process_pet_detail_workflow(entity_data: Dict[str, Any]) -> None:
    pet_id = entity_data.get('id')
    if not pet_id:
        logger.warning("pet_detail entity missing 'id' field.")
        entity_data['result_status'] = 'failed'
        entity_data['error_message'] = "'id' field is required"
        entity_data['processed_at'] = datetime.utcnow().isoformat()
        return
    try:
        await process_pet_detail(entity_data)
        entity_data['result_status'] = 'completed'
    except Exception as e:
        logger.error(f"Error processing pet_detail workflow for id {pet_id}: {e}")
        entity_data['result_status'] = 'failed'
        entity_data['error_message'] = str(e)
    finally:
        entity_data['processed_at'] = datetime.utcnow().isoformat()

async def process_pet_detail(entity_data: Dict[str, Any]) -> None:
    pet_id = entity_data.get('id')
    # Business logic to fetch pet details and update entity_data
    pet_detail = await fetch_pet_detail_from_petstore(pet_id)
    entity_data['pet_detail'] = pet_detail

# fetch_pet_detail_from_petstore should be defined elsewhere as async function that fetches pet detail from Petstore API