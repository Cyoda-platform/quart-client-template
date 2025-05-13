import httpx
from datetime import datetime
import logging

PETSTORE_BASE_URL = "https://petstore.swagger.io/v2"
logger = logging.getLogger(__name__)

async def process_order(entity):
    # Workflow orchestration: validate pet, parse ship date, update status and timestamp
    await process_validate_pet_availability(entity)
    process_parse_ship_date(entity)
    process_set_status_and_timestamp(entity)

async def process_validate_pet_availability(entity):
    pet_id = str(entity.get("petId"))
    pet = None
    try:
        # TODO: Replace with real entity_service call if available
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

    if pet.get("status") != "available":
        raise ValueError(f"Pet with id {pet_id} is not available")

def process_parse_ship_date(entity):
    ship_date_str = entity.get("shipDate")
    try:
        if ship_date_str:
            parsed_date = datetime.fromisoformat(ship_date_str)
        else:
            parsed_date = datetime.utcnow()
    except Exception:
        parsed_date = datetime.utcnow()
    entity["shipDate"] = parsed_date.isoformat()

def process_set_status_and_timestamp(entity):
    entity.setdefault("status", "placed")
    entity["processedAt"] = datetime.utcnow().isoformat()