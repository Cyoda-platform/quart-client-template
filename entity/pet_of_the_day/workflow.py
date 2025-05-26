import httpx
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

PETSTORE_BASE_URL = "https://petstore.swagger.io/v2"

async def process_fetch_available_pets(entity: dict):
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{PETSTORE_BASE_URL}/pet/findByStatus", params={"status": "available"})
            resp.raise_for_status()
            pets = resp.json()
        entity['pets'] = pets
    except Exception as e:
        logger.warning(f"Failed to fetch available pets: {e}")
        entity['pets'] = []

async def process_select_pet_with_photo(entity: dict):
    pets = entity.get('pets', [])
    for pet in pets:
        if pet.get("photoUrls"):
            entity['selected_pet'] = pet
            logger.info(f"Pet with photo selected: {pet.get('name')}")
            return
    entity['selected_pet'] = None

async def process_update_pet_of_the_day(entity: dict):
    pet = entity.get('selected_pet')
    if not pet:
        # No pet selected, clear entity attributes related to pet of the day
        entity.clear()
        return
    entity.clear()
    entity.update({
        "id": pet.get("id"),
        "name": pet.get("name"),
        "type": pet.get("category", {}).get("name", "unknown"),
        "status": pet.get("status"),
        "photoUrls": pet.get("photoUrls"),
        "funFact": f"{pet.get('name', 'This pet')} loves sunny naps! \u001f\u001f",
        "updated_at": datetime.utcnow().isoformat() + "Z"
    })
    logger.info(f"Selected pet of the day: {pet.get('name')}")

async def process_pet_of_the_day(entity: dict):
    # workflow orchestration only
    await process_fetch_available_pets(entity)
    await process_select_pet_with_photo(entity)
    await process_update_pet_of_the_day(entity)