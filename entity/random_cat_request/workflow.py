import logging
import uuid
from datetime import datetime
import httpx

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

async def fetch_random_cat(include_breed_info: bool):
    url = "https://api.thecatapi.com/v1/images/search"
    params = {"include_breeds": "1" if include_breed_info else "0"}

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()
            if not data or len(data) == 0:
                raise ValueError("No cat data returned from external API")
            return data[0]
    except Exception as e:
        logger.exception("Error fetching cat data from external API")
        raise

async def process_fetch_cat_data(entity):
    cat_raw = await fetch_random_cat(entity.get("includeBreedInfo", True))
    entity["catRaw"] = cat_raw

async def process_extract_breed_info(entity):
    cat_raw = entity.get("catRaw")
    breed_info = None
    if entity.get("includeBreedInfo", True) and cat_raw and cat_raw.get("breeds"):
        breed = cat_raw["breeds"][0]
        breed_info = {
            "name": breed.get("name"),
            "origin": breed.get("origin"),
            "temperament": breed.get("temperament"),
            "description": breed.get("description"),
        }
    entity["breed"] = breed_info

async def process_update_entity_with_cat_data(entity):
    cat_raw = entity.get("catRaw")
    entity["imageUrl"] = cat_raw.get("url") if cat_raw else None
    entity["fetchedAt"] = datetime.utcnow().isoformat() + "Z"
    entity["status"] = "completed"
    entity["completedAt"] = datetime.utcnow().isoformat() + "Z"
    # Remove redundant catRaw after processing
    entity.pop("catRaw", None)

async def process_handle_failure(entity, exc):
    entity["status"] = "failed"
    entity["error"] = str(exc)
    entity["completedAt"] = datetime.utcnow().isoformat() + "Z"
    # Remove redundant catRaw if any
    entity.pop("catRaw", None)