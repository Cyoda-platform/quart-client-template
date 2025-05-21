import asyncio
import logging
import httpx

PETSTORE_BASE_URL = "https://petstore.swagger.io/v2"
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

async def process_pet_search_request(entity):
    # Workflow orchestration only
    if "status" not in entity:
        entity["status"] = "processing"
    await process_fetch_pet_search_results(entity)
    return entity

async def process_fetch_pet_search_results(entity):
    try:
        async with httpx.AsyncClient() as client:
            params = {"status": entity.get("status_filter")} if entity.get("status_filter") else {}
            resp = await client.get(f"{PETSTORE_BASE_URL}/pet/findByStatus", params=params)
            resp.raise_for_status()
            pets = resp.json()
            category_filter = entity.get("category_filter")
            if category_filter:
                pets = [
                    pet for pet in pets
                    if pet.get("category") and pet["category"].get("name", "").lower() == category_filter.lower()
                ]
            results = []
            for pet in pets:
                results.append({
                    "id": pet.get("id"),
                    "name": pet.get("name"),
                    "category": pet.get("category", {}).get("name"),
                    "status": pet.get("status"),
                    "description": None  # TODO: Add description if available
                })
            entity["results"] = results
            entity["status"] = "completed"
            logger.info(f"Pet search results fetched and stored. Total: {len(results)} pets.")
    except Exception as e:
        entity["status"] = "failed"
        logger.exception(f"Error fetching pet search results: {e}")

async def process_pet_details_request(entity):
    if "status" not in entity:
        entity["status"] = "processing"
    pet_ids = entity.get("petIds", [])
    pets = await asyncio.gather(*(process_fetch_pet_detail(pet_id) for pet_id in pet_ids))
    entity["pets"] = [pet for pet in pets if pet is not None]
    entity["status"] = "completed" if len(entity["pets"]) == len(pet_ids) else "partial_failed"
    return entity

async def process_fetch_pet_detail(pet_id):
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{PETSTORE_BASE_URL}/pet/{pet_id}")
            resp.raise_for_status()
            pet = resp.json()
            name = pet.get("name", "Mysterious Pet")
            category = pet.get("category", {}).get("name", "Unknown Category")
            status = pet.get("status", "unknown")
            fun_description = f"{name} is a wonderful {category.lower()} currently {status} and waiting for a loving home! 😻"
            return {
                "id": pet_id,
                "name": name,
                "category": category,
                "status": status,
                "funDescription": fun_description,
            }
    except Exception as e:
        logger.exception(f"Error fetching details for pet {pet_id}: {e}")
        return None