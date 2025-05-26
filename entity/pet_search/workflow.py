import uuid
import httpx
import logging

logger = logging.getLogger(__name__)

PETSTORE_BASE_URL = "https://petstore.swagger.io/v2"

async def process_fetch_pets(entity: dict):
    status = entity.get('status')
    params = {}
    if status:
        params["status"] = status
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{PETSTORE_BASE_URL}/pet/findByStatus", params=params)
            resp.raise_for_status()
            pets = resp.json()
        entity['fetched_pets'] = pets
    except Exception as e:
        logger.warning(f"fetch_pets failed: {e}")
        entity['fetched_pets'] = []

async def process_filter_pets(entity: dict):
    pet_type = entity.get('type')
    pets = entity.get('fetched_pets', [])
    if pet_type:
        pets = [pet for pet in pets if pet.get("category", {}).get("name", "").lower() == pet_type.lower()]
    entity['results'] = pets
    # Clean up temporary data
    entity.pop('fetched_pets', None)

async def process_pet_search(entity: dict) -> dict:
    search_id = entity.get('search_id') or str(uuid.uuid4())
    entity['search_id'] = search_id
    entity['results'] = []
    await process_fetch_pets(entity)
    await process_filter_pets(entity)
    logger.info(f"pet_search {search_id} found {len(entity['results'])} pets")
    return entity