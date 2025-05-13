import httpx
from datetime import datetime
import logging

PETSTORE_BASE_URL = "https://petstore.swagger.io/v2"
logger = logging.getLogger(__name__)

async def process_favorite_pet(entity):
    # Workflow orchestration: validate pet existence, enrich entity
    await process_validate_pet_existence(entity)
    process_enrich_favorite_timestamp(entity)

async def process_validate_pet_existence(entity):
    pet_id = str(entity.get("id"))
    pet = None
    try:
        # TODO: Replace with real entity_service call if available
        # Here, simulate retrieval failure to fetch from external API
        pet = None
    except Exception as e:
        logger.exception(e)
        pet = None

    if pet is None:
        async with httpx.AsyncClient() as client:
            try:
                r = await client.get(f"{PETSTORE_BASE_URL}/pet/{pet_id}")
                r.raise_for_status()
                pet = r.json()
            except httpx.HTTPStatusError as ex:
                if ex.response.status_code == 404:
                    raise ValueError(f"Pet with id {pet_id} not found")
                logger.exception(ex)
                raise
            except Exception as ex:
                logger.exception(ex)
                raise

    entity["name"] = pet.get("name")
    entity["category"] = pet.get("category", {})
    entity["status"] = pet.get("status", "")

def process_enrich_favorite_timestamp(entity):
    entity["favoritedAt"] = datetime.utcnow().isoformat()