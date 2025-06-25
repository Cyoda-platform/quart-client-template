import httpx
import logging

logger = logging.getLogger(__name__)

PETSTORE_BASE = "https://petstore3.swagger.io/api/v3"

async def process_pet_adoption_request(entity: dict):
    pet_id = entity.get("pet_id")
    if not pet_id:
        entity["adoption_status"] = "failed"
        entity["error"] = "No pet_id provided"
        return entity

    await process_fetch_pet(entity)
    if entity.get("adoption_status") == "failed":
        return entity

    await process_update_pet_status(entity)
    return entity

async def process_fetch_pet(entity: dict):
    pet_id = entity.get("pet_id")
    get_url = f"{PETSTORE_BASE}/pet/{pet_id}"
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(get_url, timeout=10)
            resp.raise_for_status()
            pet = resp.json()
            if not pet:
                entity["adoption_status"] = "failed"
                entity["error"] = "Pet not found"
                return
            entity["pet_data"] = pet
            entity["adoption_status"] = "fetched"
        except Exception as e:
            logger.exception(f"Failed to fetch pet via external API: {e}")
            entity["adoption_status"] = "failed"
            entity["error"] = str(e)

async def process_update_pet_status(entity: dict):
    pet = entity.get("pet_data")
    if not pet:
        entity["adoption_status"] = "failed"
        entity["error"] = "No pet data to update"
        return
    pet["status"] = "adopted"
    update_url = f"{PETSTORE_BASE}/pet"
    async with httpx.AsyncClient() as client:
        try:
            resp_update = await client.put(update_url, json=pet, timeout=10)
            resp_update.raise_for_status()
            entity["adoption_status"] = "success"
        except Exception as e:
            logger.exception(f"Failed to update pet status via external API: {e}")
            entity["adoption_status"] = "failed"
            entity["error"] = str(e)