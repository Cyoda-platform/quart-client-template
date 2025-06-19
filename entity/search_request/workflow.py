import asyncio
import logging
import uuid
from datetime import datetime

FUN_FACTS = {
    "cat": "Cats are curious and love to explore!",
    "dog": "Dogs are loyal and friendly companions.",
    "bird": "Birds are social and enjoy singing.",
    "rabbit": "Rabbits have nearly 360-degree panoramic vision.",
}

logger = logging.getLogger(__name__)

async def process_fetch_pets(entity: dict):
    # TODO: Implement actual fetch logic here; placeholder simulates external call
    # Example: entity['pets'] = await fetch_pets_from_petstore(...)
    pass

async def process_enrich_facts(entity: dict):
    pets = entity.get("pets", [])
    for pet in pets:
        fact = FUN_FACTS.get(pet.get("type", "").lower(), "Every pet is unique and special!")
        pet["funFact"] = fact

async def process_store_results(entity: dict):
    search_id = entity["id"]
    _search_results_cache[search_id] = {
        "requestedAt": datetime.utcnow().isoformat() + "Z",
        "criteria": entity,
        "pets": entity.get("pets", []),
        "status": "completed",
    }
    logger.info(f"Search completed for searchId={search_id}, {len(entity.get('pets', []))} pets found")

async def process_handle_failure(entity: dict, error: Exception):
    search_id = entity["id"]
    logger.exception(f"Failed processing search {search_id}: {error}")
    _search_results_cache[search_id] = {
        "requestedAt": datetime.utcnow().isoformat() + "Z",
        "criteria": entity,
        "pets": [],
        "status": "failed",
    }

async def process_search_request(entity: dict):
    search_id = entity.get("id")
    if not search_id:
        search_id = str(uuid.uuid4())
        entity["id"] = search_id
    try:
        await process_fetch_pets(entity)
        await process_enrich_facts(entity)
        await process_store_results(entity)
    except Exception as e:
        await process_handle_failure(entity, e)