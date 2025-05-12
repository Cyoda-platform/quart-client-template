import httpx
import logging
from typing import Dict

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

async def process_set_breed(entity: Dict):
    if not entity.get("breed") and entity.get("name"):
        entity["breed"] = entity["name"]

async def process_enrich_image(entity: Dict):
    breed = entity.get("breed")
    if not entity.get("image_url") and breed:
        try:
            async with httpx.AsyncClient() as client:
                breeds_resp = await client.get("https://api.thecatapi.com/v1/breeds", timeout=10)
                breeds_resp.raise_for_status()
                breeds = breeds_resp.json()
                breed_id = None
                for b in breeds:
                    if b["name"].lower() == breed.lower():
                        breed_id = b["id"]
                        break
                if breed_id:
                    img_resp = await client.get(
                        f"https://api.thecatapi.com/v1/images/search?breed_id={breed_id}&limit=1", timeout=10
                    )
                    img_resp.raise_for_status()
                    imgs = img_resp.json()
                    if imgs and imgs[0].get("url"):
                        entity["image_url"] = imgs[0]["url"]
        except Exception as e:
            logger.warning(f"Failed to enrich cat image_url: {e}")

async def process_set_fact(entity: Dict):
    if not entity.get("fact") and entity.get("breed"):
        entity["fact"] = f"{entity['breed']} is a wonderful cat breed!"

async def process_cat(entity: Dict) -> Dict:
    # Workflow orchestration only
    await process_set_breed(entity)
    await process_enrich_image(entity)
    await process_set_fact(entity)
    return entity