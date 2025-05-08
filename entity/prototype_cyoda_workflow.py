from dataclasses import dataclass
from typing import Dict, Any, List, Optional

import logging
from datetime import datetime

import httpx
from quart import Quart, jsonify
from quart_schema import QuartSchema, validate_request, validate_querystring

from app_init.app_init import BeanFactory
from common.config.config import ENTITY_VERSION

factory = BeanFactory(config={'CHAT_REPOSITORY': 'cyoda'})
entity_service = factory.get_services()['entity_service']
cyoda_auth_service = factory.get_services()["cyoda_auth_service"]

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)


@dataclass
class BreedFilter:
    origin: Optional[str] = None
    temperament: Optional[str] = None


@dataclass
class FactsRequest:
    count: int


@dataclass
class ImagesRequest:
    breed_id: Optional[str] = None
    limit: int = 5


@dataclass
class FavoriteRequest:
    user_id: str
    item_type: str  # "breed" | "fact" | "image"
    item_id: str


THECATAPI_KEY = ""  # Optional but recommended to avoid rate limits
THECATAPI_BASE = "https://api.thecatapi.com/v1"
CATFACTS_BASE = "https://catfact.ninja"

headers = {}
if THECATAPI_KEY:
    headers["x-api-key"] = THECATAPI_KEY


async def fetch_cat_breeds(filter_data: Dict[str, Optional[str]]) -> List[Dict[str, Any]]:
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get(f"{THECATAPI_BASE}/breeds", headers=headers, timeout=10)
            r.raise_for_status()
            breeds = r.json()
    except Exception as e:
        logger.exception("Error fetching cat breeds: %s", e)
        return []

    filtered = []
    origin_filter = filter_data.get("origin")
    temperament_filter = filter_data.get("temperament")

    for breed in breeds:
        origin = breed.get("origin", "").lower()
        temperament = breed.get("temperament", "").lower()
        if origin_filter and origin_filter.lower() not in origin:
            continue
        if temperament_filter and temperament_filter.lower() not in temperament:
            continue

        filtered.append(
            {
                "id": breed.get("id"),
                "name": breed.get("name"),
                "origin": breed.get("origin"),
                "temperament": breed.get("temperament"),
                "description": breed.get("description"),
                "image_url": breed.get("image", {}).get("url"),
            }
        )
    return filtered


async def fetch_cat_facts(count: int) -> List[str]:
    facts = []
    try:
        async with httpx.AsyncClient() as client:
            limit = min(count, 500)
            r = await client.get(f"{CATFACTS_BASE}/facts?limit={limit}", timeout=10)
            r.raise_for_status()
            data = r.json()
            facts = [fact["fact"] for fact in data.get("data", [])]
    except Exception as e:
        logger.exception("Error fetching cat facts: %s", e)
    return facts


async def fetch_cat_images(breed_id: Optional[str], limit: int) -> List[Dict[str, Any]]:
    params = {"limit": limit}
    if breed_id:
        params["breed_id"] = breed_id

    try:
        async with httpx.AsyncClient() as client:
            r = await client.get(f"{THECATAPI_BASE}/images/search", headers=headers, params=params, timeout=10)
            r.raise_for_status()
            images = r.json()
            result = []
            for img in images:
                breed_ids = [b.get("id") for b in img.get("breeds", [])] if img.get("breeds") else []
                result.append(
                    {
                        "id": img.get("id"),
                        "url": img.get("url"),
                        "breed_id": breed_ids[0] if breed_ids else None,
                    }
                )
            return result
    except Exception as e:
        logger.exception("Error fetching cat images: %s", e)
        return []


async def process_breeds_request(entity: Dict[str, Any]) -> Dict[str, Any]:
    filter_data = {
        "origin": entity.get("origin"),
        "temperament": entity.get("temperament"),
    }
    breeds = await fetch_cat_breeds(filter_data)

    for breed in breeds:
        try:
            await entity_service.add_item(
                token=cyoda_auth_service,
                entity_model="breeds",
                entity_version=ENTITY_VERSION,
                entity=breed,
                workflow=process_breeds,
            )
        except Exception as e:
            logger.exception("Failed to add breed entity: %s", e)

    entity["processed_at"] = datetime.utcnow().isoformat()
    entity["fetched_count"] = len(breeds)
    return entity


async def process_facts_request(entity: Dict[str, Any]) -> Dict[str, Any]:
    count = entity.get("count", 5)
    facts = await fetch_cat_facts(count)

    for fact in facts:
        try:
            await entity_service.add_item(
                token=cyoda_auth_service,
                entity_model="facts",
                entity_version=ENTITY_VERSION,
                entity={"fact": fact},
                workflow=process_facts,
            )
        except Exception as e:
            logger.exception("Failed to add fact entity: %s", e)

    entity["processed_at"] = datetime.utcnow().isoformat()
    entity["fetched_count"] = len(facts)
    return entity


async def process_images_request(entity: Dict[str, Any]) -> Dict[str, Any]:
    breed_id = entity.get("breed_id")
    limit = entity.get("limit", 5)

    images = await fetch_cat_images(breed_id, limit)

    for image in images:
        try:
            await entity_service.add_item(
                token=cyoda_auth_service,
                entity_model="images",
                entity_version=ENTITY_VERSION,
                entity=image,
                workflow=process_images,
            )
        except Exception as e:
            logger.exception("Failed to add image entity: %s", e)

    entity["processed_at"] = datetime.utcnow().isoformat()
    entity["fetched_count"] = len(images)
    return entity


async def process_breeds(entity: Dict[str, Any]) -> Dict[str, Any]:
    entity["processed_at"] = datetime.utcnow().isoformat()
    return entity


async def process_facts(entity: Dict[str, Any]) -> Dict[str, Any]:
    entity["source"] = "catfact.ninja"
    entity["processed_at"] = datetime.utcnow().isoformat()
    return entity


async def process_images(entity: Dict[str, Any]) -> Dict[str, Any]:
    entity["processed_at"] = datetime.utcnow().isoformat()
    return entity


async def process_favorites(entity: Dict[str, Any]) -> Dict[str, Any]:
    entity["added_at"] = datetime.utcnow().isoformat()
    return entity


@app.route("/cats/breeds", methods=["POST"])
@validate_request(BreedFilter)
async def post_cats_breeds(data: BreedFilter):
    entity = data.__dict__
    try:
        await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model="breeds_request",
            entity_version=ENTITY_VERSION,
            entity=entity,
            workflow=process_breeds_request,
        )
        return jsonify({"message": "Breeds request accepted"}), 202
    except Exception as e:
        logger.exception("Failed to submit breeds request: %s", e)
        return jsonify({"message": "Failed to submit breeds request"}), 500


@app.route("/cats/breeds", methods=["GET"])
@validate_querystring(BreedFilter)
async def get_cats_breeds():
    try:
        breeds = await entity_service.get_items(
            token=cyoda_auth_service,
            entity_model="breeds",
            entity_version=ENTITY_VERSION,
        )
    except Exception as e:
        logger.exception("Failed to get breeds: %s", e)
        breeds = []
    return jsonify({"breeds": breeds or []})


@app.route("/cats/facts", methods=["POST"])
@validate_request(FactsRequest)
async def post_cats_facts(data: FactsRequest):
    entity = data.__dict__
    try:
        await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model="facts_request",
            entity_version=ENTITY_VERSION,
            entity=entity,
            workflow=process_facts_request,
        )
        return jsonify({"message": "Facts request accepted"}), 202
    except Exception as e:
        logger.exception("Failed to submit facts request: %s", e)
        return jsonify({"message": "Failed to submit facts request"}), 500


@app.route("/cats/facts", methods=["GET"])
async def get_cats_facts():
    try:
        facts = await entity_service.get_items(
            token=cyoda_auth_service,
            entity_model="facts",
            entity_version=ENTITY_VERSION,
        )
    except Exception as e:
        logger.exception("Failed to get facts: %s", e)
        facts = []
    return jsonify({"facts": facts or []})


@app.route("/cats/images", methods=["POST"])
@validate_request(ImagesRequest)
async def post_cats_images(data: ImagesRequest):
    entity = data.__dict__
    try:
        await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model="images_request",
            entity_version=ENTITY_VERSION,
            entity=entity,
            workflow=process_images_request,
        )
        return jsonify({"message": "Images request accepted"}), 202
    except Exception as e:
        logger.exception("Failed to submit images request: %s", e)
        return jsonify({"message": "Failed to submit images request"}), 500


@app.route("/cats/images", methods=["GET"])
async def get_cats_images():
    try:
        images = await entity_service.get_items(
            token=cyoda_auth_service,
            entity_model="images",
            entity_version=ENTITY_VERSION,
        )
    except Exception as e:
        logger.exception("Failed to get images: %s", e)
        images = []
    return jsonify({"images": images or []})


@app.route("/favorites", methods=["POST"])
@validate_request(FavoriteRequest)
async def post_favorites(data: FavoriteRequest):
    try:
        fav_id = await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model="favorites",
            entity_version=ENTITY_VERSION,
            entity=data.__dict__,
            workflow=process_favorites,
        )
        return jsonify({"success": True, "id": fav_id, "message": "Added to favorites"})
    except Exception as e:
        logger.exception("Failed to add to favorites: %s", e)
        return jsonify({"success": False, "message": "Failed to add to favorites"}), 500


@app.route("/favorites/<string:user_id>", methods=["GET"])
async def get_favorites(user_id):
    try:
        condition = {"user_id": user_id}
        favs = await entity_service.get_items_by_condition(
            token=cyoda_auth_service,
            entity_model="favorites",
            entity_version=ENTITY_VERSION,
            condition=condition,
        )
    except Exception as e:
        logger.exception("Failed to get favorites: %s", e)
        favs = []
    return jsonify({"favorites": favs or []})


if __name__ == "__main__":
    import logging

    logging.basicConfig(level=logging.INFO)
    app.run(use_reloader=False, debug=True, host="0.0.0.0", port=8000, threaded=True)