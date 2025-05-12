import httpx
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

CAT_API_BASE = "https://api.thecatapi.com/v1"
CAT_FACTS_API = "https://catfact.ninja/fact"

async def process_breed_search(entity: dict):
    breed_name = entity.get("breed_name")
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{CAT_API_BASE}/breeds/search", params={"q": breed_name})
        resp.raise_for_status()
        breeds = resp.json()
        if breeds:
            entity["breed_id"] = breeds[0]["id"]
        else:
            entity["breed_id"] = None

async def process_fetch_images(entity: dict):
    params = {"limit": 5}
    breed_id = entity.get("breed_id")
    if breed_id:
        params["breed_ids"] = breed_id
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{CAT_API_BASE}/images/search", params=params)
        resp.raise_for_status()
        images = resp.json()
        entity["images"] = images

async def process_fetch_facts(entity: dict):
    images = entity.get("images", [])
    facts = []
    async with httpx.AsyncClient() as client:
        for _ in range(len(images)):
            try:
                fact_resp = await client.get(CAT_FACTS_API)
                fact_resp.raise_for_status()
                fact_data = fact_resp.json()
                facts.append(fact_data.get("fact", "Cats are mysterious creatures."))
            except Exception as e:
                logger.exception("Failed to fetch cat fact")
                facts.append("Cats are mysterious creatures.")
    entity["facts"] = facts

async def process_enrich_cats(entity: dict):
    cats = []
    images = entity.get("images", [])
    facts = entity.get("facts", [])
    breed_name = entity.get("breed_name")
    for i, img in enumerate(images):
        cat_breeds = img.get("breeds", [])
        cat_breed = cat_breeds[0]["name"] if cat_breeds else (breed_name or "Unknown")
        cats.append({
            "id": img.get("id"),
            "breed": cat_breed,
            "image_url": img.get("url"),
            "fact": facts[i] if i < len(facts) else "Cats are wonderful."
        })
    entity["cats"] = cats

async def process_cats(entity: dict) -> dict:
    logger.info(f"Workflow process_cats started for entity: {entity}")
    try:
        input_type = entity.get("type")
        breed_name = entity.get("breed_name")
        entity["status"] = "processing"

        if input_type == "breed" and breed_name:
            await process_breed_search(entity)
            if not entity.get("breed_id"):
                entity["cats"] = []
                entity["status"] = "completed"
                entity["message"] = f"No breed found matching '{breed_name}'"
                logger.info(entity["message"])
                return entity

        await process_fetch_images(entity)
        images = entity.get("images")
        if not images:
            entity["cats"] = []
            entity["status"] = "completed"
            entity["message"] = "No cat images found"
            logger.info(entity["message"])
            return entity

        await process_fetch_facts(entity)
        await process_enrich_cats(entity)

        entity["status"] = "completed"
        entity["persisted_at"] = datetime.utcnow().isoformat()

        # Clean up temp keys
        entity.pop("breed_id", None)
        entity.pop("images", None)
        entity.pop("facts", None)

    except Exception as e:
        logger.exception("Error in process_cats workflow")
        entity["cats"] = []
        entity["status"] = "failed"
        entity["message"] = str(e)

    logger.info("Workflow process_cats finished")
    return entity