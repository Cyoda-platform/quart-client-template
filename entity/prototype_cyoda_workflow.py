from dataclasses import dataclass
from typing import Optional, Dict, List
import asyncio
import logging
from datetime import datetime

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request

from app_init.app_init import BeanFactory
from common.config.config import ENTITY_VERSION

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

factory = BeanFactory(config={'CHAT_REPOSITORY': 'cyoda'})
entity_service = factory.get_services()['entity_service']
cyoda_auth_service = factory.get_services()["cyoda_auth_service"]

app = Quart(__name__)
QuartSchema(app)

entity_name = "cat"
fetch_job_entity_name = "cat_fetch_job"

PETSTORE_BASE_URL = "https://petstore.swagger.io/v2"


def generate_job_id() -> str:
    return datetime.utcnow().strftime("%Y%m%d%H%M%S%f")


def transform_pet_to_cat(pet: Dict) -> Dict:
    return {
        "id": str(pet.get("id")),
        "name": pet.get("name", "Unknown Cat"),
        "breed": pet.get("category", {}).get("name", "Unknown Breed"),
        "age": pet.get("age", 2),  # TODO: No age in Petstore API, use dummy
        "description": pet.get("description", "No description available"),
        "imageUrl": pet.get("photoUrls", [None])[0] if pet.get("photoUrls") else None,
    }


@dataclass
class AgeRange:
    min: Optional[int] = None
    max: Optional[int] = None


@dataclass
class FetchFilters:
    breed: Optional[str] = None
    ageRange: Optional[Dict] = None
    limit: Optional[int] = 10


@dataclass
class SearchFilters:
    breed: Optional[str] = None
    ageRange: Optional[Dict] = None
    nameContains: Optional[str] = None


@dataclass
class SearchRequest:
    filters: Optional[Dict] = None
    sortBy: Optional[str] = None
    limit: Optional[int] = 10


async def fetch_cats_from_petstore(filters: Dict) -> List[Dict]:
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.get(f"{PETSTORE_BASE_URL}/pet/findByStatus", params={"status": "available"})
            resp.raise_for_status()
            pets = resp.json()

            breed_filter = filters.get("breed")
            age_min = filters.get("ageRange", {}).get("min") if filters.get("ageRange") else None
            age_max = filters.get("ageRange", {}).get("max") if filters.get("ageRange") else None
            limit = filters.get("limit") or 10

            cats = []
            for pet in pets:
                cat = transform_pet_to_cat(pet)
                if breed_filter and isinstance(cat.get("breed"), str) and breed_filter.lower() != cat["breed"].lower():
                    continue
                if age_min is not None and cat.get("age", 0) < age_min:
                    continue
                if age_max is not None and cat.get("age", 0) > age_max:
                    continue
                cats.append(cat)
                if len(cats) >= limit:
                    break

            return cats

        except (httpx.HTTPError, httpx.RequestError) as e:
            logger.exception("Failed to fetch cats from Petstore API")
            return []


async def process_cat(entity: Dict) -> Dict:
    entity["processedAt"] = datetime.utcnow().isoformat()

    if "breed" in entity and isinstance(entity["breed"], str):
        entity["breed"] = entity["breed"].title()

    # Ensure name is string, fallback to Unknown
    if "name" not in entity or not isinstance(entity["name"], str):
        entity["name"] = "Unknown Cat"

    # Ensure age is int and non-negative
    try:
        age = int(entity.get("age", 2))
        if age < 0:
            age = 2
    except Exception:
        age = 2
    entity["age"] = age

    # Normalize imageUrl to None if empty string or invalid
    image_url = entity.get("imageUrl")
    if not image_url or not isinstance(image_url, str) or image_url.strip() == "":
        entity["imageUrl"] = None

    return entity


async def process_cat_fetch_job(entity: Dict) -> Dict:
    filters = entity.get("filters", {})
    logger.info(f"Processing cat fetch job with filters: {filters}")

    try:
        cats = await fetch_cats_from_petstore(filters)
        logger.info(f"Fetched {len(cats)} cats from Petstore API")
    except Exception:
        logger.exception("Failed during fetching cats")
        cats = []

    # Add a semaphore to limit concurrency of add_item to avoid overwhelming the service
    semaphore = asyncio.Semaphore(5)

    async def add_cat(cat):
        async with semaphore:
            try:
                await entity_service.add_item(
                    token=cyoda_auth_service,
                    entity_model=entity_name,
                    entity_version=ENTITY_VERSION,
                    entity=cat,
                    workflow=process_cat
                )
            except Exception:
                logger.exception(f"Failed to add cat {cat.get('id')} to entity service")

    tasks = [add_cat(cat) for cat in cats]
    await asyncio.gather(*tasks)

    entity["status"] = "completed"
    entity["fetchedCount"] = len(cats)
    entity["completedAt"] = datetime.utcnow().isoformat()

    return entity


@app.route("/cats/fetch", methods=["POST"])
@validate_request(FetchFilters)
async def fetch_cats(data: FetchFilters):
    job_entity = {
        "filters": data.__dict__,
        "status": "processing",
        "requestedAt": datetime.utcnow().isoformat(),
        "jobId": generate_job_id(),
    }

    try:
        job_entity_id = await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model=fetch_job_entity_name,
            entity_version=ENTITY_VERSION,
            entity=job_entity,
            workflow=process_cat_fetch_job,
        )
    except Exception:
        logger.exception("Failed to create cat fetch job entity")
        return jsonify({"error": "Failed to start cat fetch job"}), 500

    return jsonify({
        "status": "processing",
        "jobId": job_entity["jobId"],
        "message": "Cat fetching job started"
    }), 202


@app.route("/cats", methods=["GET"])
async def get_cats():
    breed = request.args.get("breed")
    age_min = request.args.get("ageMin", type=int)
    age_max = request.args.get("ageMax", type=int)
    limit = request.args.get("limit", default=10, type=int)

    try:
        cats = await entity_service.get_items(
            token=cyoda_auth_service,
            entity_model=entity_name,
            entity_version=ENTITY_VERSION,
        )
    except Exception:
        logger.exception("Failed to get cats from entity service")
        return jsonify([]), 500

    filtered_cats = cats

    if breed and isinstance(breed, str):
        filtered_cats = [c for c in filtered_cats if isinstance(c.get("breed"), str) and c.get("breed").lower() == breed.lower()]
    if age_min is not None:
        filtered_cats = [c for c in filtered_cats if isinstance(c.get("age"), int) and c.get("age") >= age_min]
    if age_max is not None:
        filtered_cats = [c for c in filtered_cats if isinstance(c.get("age"), int) and c.get("age") <= age_max]

    # Defensive: ensure limit is positive and sane
    if limit <= 0 or limit > 100:
        limit = 10

    return jsonify(filtered_cats[:limit])


@app.route("/cats/search", methods=["POST"])
@validate_request(SearchRequest)
async def search_cats(data: SearchRequest):
    filters = data.filters or {}
    sort_by = data.sortBy
    limit = data.limit or 10

    conditions = []

    breed = filters.get("breed")
    age_range = filters.get("ageRange", {})
    name_contains = filters.get("nameContains")

    if breed and isinstance(breed, str):
        conditions.append({"field": "breed", "operator": "eq", "value": breed})
    if age_range and isinstance(age_range, dict):
        min_age = age_range.get("min")
        max_age = age_range.get("max")
        if isinstance(min_age, int):
            conditions.append({"field": "age", "operator": "gte", "value": min_age})
        if isinstance(max_age, int):
            conditions.append({"field": "age", "operator": "lte", "value": max_age})

    try:
        if conditions:
            cats = await entity_service.get_items_by_condition(
                token=cyoda_auth_service,
                entity_model=entity_name,
                entity_version=ENTITY_VERSION,
                condition=conditions,
            )
        else:
            cats = await entity_service.get_items(
                token=cyoda_auth_service,
                entity_model=entity_name,
                entity_version=ENTITY_VERSION,
            )
    except Exception:
        logger.exception("Failed to get cats from entity service")
        return jsonify([]), 500

    result_cats = cats

    if name_contains and isinstance(name_contains, str):
        name_contains_lower = name_contains.lower()
        result_cats = [c for c in result_cats if isinstance(c.get("name"), str) and name_contains_lower in c.get("name").lower()]

    if sort_by in {"age", "breed", "name"}:
        try:
            result_cats = sorted(result_cats, key=lambda c: c.get(sort_by) or "")
        except Exception:
            logger.exception("Sorting failed")

    # Defensive: limit sanity
    if limit <= 0 or limit > 100:
        limit = 10

    return jsonify(result_cats[:limit])


if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)