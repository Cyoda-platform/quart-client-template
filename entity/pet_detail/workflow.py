import asyncio
import logging
import httpx

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

async def process_pet_detail(entity):
    # Workflow orchestration only
    if entity.get("status") in ("completed", "failed"):
        return entity
    entity["status"] = "processing"
    await process_fetch_pet_data(entity)
    return entity

async def process_fetch_pet_data(entity):
    pet_id = entity.get("id")
    if not pet_id:
        logger.warning("pet_detail entity missing 'id'")
        entity["status"] = "failed"
        entity["data"] = None
        return
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"https://petstore.swagger.io/v2/pet/{pet_id}")
            resp.raise_for_status()
            pet = resp.json()
        name = pet.get("name", "Mysterious Pet")
        category = pet.get("category", {}).get("name", "Unknown Category")
        status = pet.get("status", "unknown")
        fun_description = f"{name} is a wonderful {category.lower()} currently {status} and waiting for a loving home! 😻"
        enriched = {
            "id": pet_id,
            "name": name,
            "category": category,
            "status": status,
            "funDescription": fun_description,
        }
        entity["status"] = "completed"
        entity["data"] = enriched
    except (httpx.RequestError, httpx.HTTPStatusError) as e:
        logger.warning(f"HTTP error fetching pet_detail for id {pet_id}: {e}")
        entity["status"] = "failed"
        entity["data"] = None
    except Exception as e:
        logger.exception(f"Unexpected error enriching pet_detail entity with id {pet_id}: {e}")
        entity["status"] = "failed"
        entity["data"] = None