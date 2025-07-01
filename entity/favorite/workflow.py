from datetime import datetime
import httpx
import logging

logger = logging.getLogger(__name__)
PETSTORE_BASE_URL = "https://petstore3.swagger.io/api/v3"

async def _add_timestamp(entity: dict):
    if "added_at" not in entity:
        entity["added_at"] = datetime.utcnow().isoformat()

async def _enrich_with_pet_info(entity: dict):
    pet_id = entity.get("pet_id")
    if not pet_id:
        logger.warning("Favorite entity missing pet_id, skipping enrichment")
        return
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            url = f"{PETSTORE_BASE_URL}/pet/{pet_id}"
            resp = await client.get(url)
            if resp.status_code == 200:
                pet = resp.json()
                entity["pet_name"] = pet.get("name")
                entity["pet_category"] = pet.get("category", {}).get("name")
            else:
                logger.warning(f"Failed to fetch pet info for pet_id {pet_id}, status: {resp.status_code}")
        except Exception as e:
            logger.exception(f"Exception during fetching pet info for pet_id {pet_id}: {e}")

async def process_favorite(entity: dict):
    # Workflow orchestration only - no business logic here
    await _add_timestamp(entity)
    await _enrich_with_pet_info(entity)