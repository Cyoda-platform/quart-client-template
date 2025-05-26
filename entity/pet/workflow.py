from datetime import datetime
import asyncio
import logging

logger = logging.getLogger(__name__)

async def process_pet(entity: dict) -> dict:
    # Workflow orchestration only
    await process_add_timestamp(entity)
    process_normalize_type(entity)
    await process_enrich_category_details(entity)
    process_fire_and_forget_pet_log(entity)
    logger.info(f"Processed pet entity before persistence: {entity}")
    return entity

async def process_add_timestamp(entity: dict):
    if 'created_at' not in entity:
        entity['created_at'] = datetime.utcnow().isoformat() + "Z"

def process_normalize_type(entity: dict):
    if 'type' in entity and isinstance(entity['type'], str):
        entity['type'] = entity['type'].lower()

async def process_enrich_category_details(entity: dict):
    category_name = entity.get('category', {}).get('name')
    if category_name:
        try:
            category_details = await entity_service.get_item(
                token=cyoda_auth_service,
                entity_model="category",
                entity_version=ENTITY_VERSION,
                technical_id=category_name.lower()
            )
            entity['category_details'] = category_details or {}
        except Exception as e:
            logger.warning(f"Failed to fetch category details for '{category_name}': {e}")

def process_fire_and_forget_pet_log(entity: dict):
    async def add_pet_log():
        try:
            await entity_service.add_item(
                token=cyoda_auth_service,
                entity_model="pet_log",
                entity_version=ENTITY_VERSION,
                entity={
                    "pet_id": entity.get("id"),
                    "action": "created",
                    "timestamp": datetime.utcnow().isoformat() + "Z"
                }
            )
        except Exception as e:
            logger.warning(f"Failed to add pet_log entity: {e}")
    asyncio.create_task(add_pet_log())