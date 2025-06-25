import httpx
import logging
from common.config.config import ENTITY_VERSION

logger = logging.getLogger(__name__)

PETSTORE_BASE = "https://petstore3.swagger.io/api/v3"

async def process_pet_fetch_request(entity: dict):
    # Orchestrate workflow
    pets = await process_fetch_pets(entity)
    await process_add_pets(pets)
    entity['fetch_completed'] = True

async def process_fetch_pets(entity: dict):
    type_filter = entity.get("type")
    status_filter = entity.get("status") or "available"

    url = f"{PETSTORE_BASE}/pet/findByStatus"
    params = {"status": status_filter}
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(url, params=params, timeout=10)
            resp.raise_for_status()
            pets = resp.json()
        except Exception as e:
            logger.exception(f"Failed fetching pets from Petstore API: {e}")
            pets = []

    if type_filter:
        pets = [pet for pet in pets if pet.get("category", {}).get("name", "").lower() == type_filter.lower()]
    return pets

async def process_add_pets(pets: list):
    for pet in pets:
        try:
            pet_data = pet.copy()
            pet_data.pop("id", None)
            if not isinstance(pet_data, dict):
                continue
            # TODO: entity_service and cyoda_auth_service are external dependencies,
            # here only the call placeholder is given
            await entity_service.add_item(
                token=cyoda_auth_service,
                entity_model="pet",
                entity_version=ENTITY_VERSION,
                entity=pet_data,
                workflow=process_pet
            )
        except Exception as e:
            logger.exception(f"Failed to add pet to entity_service: {e}")