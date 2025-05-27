import httpx
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

async def process_fetch_pet_detail(entity: dict):
    pet_id = entity.get("id") or entity.get("petId")
    if not pet_id:
        logger.warning("No petId provided to process_fetch_pet_detail")
        return

    url = f"https://petstore.swagger.io/v2/pet/{pet_id}"
    async with httpx.AsyncClient() as client:
        try:
            r = await client.get(url)
            r.raise_for_status()
            pet_detail = r.json()
            entity["fetched_detail"] = {
                "id": str(pet_detail.get("id")),
                "name": pet_detail.get("name"),
                "category": pet_detail.get("category", {}).get("name") if pet_detail.get("category") else None,
                "status": pet_detail.get("status"),
                "photoUrls": pet_detail.get("photoUrls"),
                "tags": pet_detail.get("tags"),
                "processed_at": datetime.utcnow().isoformat() + 'Z',
            }
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.warning(f"Pet with id {pet_id} not found in petstore")
            else:
                logger.exception(f"HTTP error fetching pet detail for id={pet_id}")
        except Exception:
            logger.exception(f"Failed to fetch pet detail for id={pet_id}")

async def process_update_timestamps(entity: dict):
    entity['detail_fetched_at'] = datetime.utcnow().isoformat() + 'Z'

async def process_pet_detail(entity: dict) -> dict:
    # Workflow orchestration only
    await process_fetch_pet_detail(entity)
    await process_update_timestamps(entity)
    return entity