import asyncio
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

async def process_pet_search_filters(entity):
    entity['processed_at'] = datetime.utcnow().isoformat()

    pets = await process_fetch_pets(entity)
    pet_results = process_format_pet_results(pets)
    await process_save_pet_search_results(entity, pet_results)

async def process_fetch_pets(entity):
    conditions = []

    if entity.get("status"):
        conditions.append({
            "jsonPath": "$.status",
            "operatorType": "EQUALS",
            "value": entity["status"],
            "type": "simple"
        })

    if entity.get("type"):
        conditions.append({
            "jsonPath": "$.category.name",
            "operatorType": "IEQUALS",
            "value": entity["type"],
            "type": "simple"
        })

    if entity.get("breed"):
        conditions.append({
            "jsonPath": "$.name",
            "operatorType": "IEQUALS",
            "value": entity["breed"],
            "type": "simple"
        })

    condition = {
        "cyoda": {
            "type": "group",
            "operator": "AND",
            "conditions": conditions
        }
    }

    try:
        pets = await entity_service.get_items_by_condition(
            token=cyoda_auth_service,
            entity_model="pet",
            entity_version=ENTITY_VERSION,
            condition=condition
        )
    except Exception as e:
        logger.error(f"Error fetching pets in workflow: {e}")
        pets = []
    return pets

def process_format_pet_results(pets):
    pet_results = []
    for pet in pets:
        pet_results.append({
            "id": pet.get("id"),
            "name": pet.get("name"),
            "type": pet.get("category", {}).get("name"),
            "breed": pet.get("name"),
            "status": pet.get("status"),
            "photoUrls": pet.get("photoUrls", [])
        })
    return pet_results

async def process_save_pet_search_results(entity, pet_results):
    try:
        search_filter_id = entity.get("id")
        if not search_filter_id:
            search_filter_id = f"temp-{datetime.utcnow().timestamp()}"

        await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model="pet_search_results",
            entity_version=ENTITY_VERSION,
            entity={
                "search_filter_id": search_filter_id,
                "timestamp": datetime.utcnow().isoformat(),
                "results": pet_results
            },
            workflow=None  # No workflow on results entity to prevent recursion
        )
    except Exception as e:
        logger.error(f"Failed to save pet_search_results entity: {e}")