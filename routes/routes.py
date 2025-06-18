from dataclasses import dataclass
import logging
from datetime import datetime
from typing import Dict, List, Optional

import httpx
from quart import Quart, jsonify
from quart_schema import QuartSchema, validate_request

from app_init.app_init import BeanFactory
from common.config.config import ENTITY_VERSION

factory = BeanFactory(config={'CHAT_REPOSITORY': 'cyoda'})
entity_service = factory.get_services()['entity_service']
cyoda_auth_service = factory.get_services()["cyoda_auth_service"]

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# Request schemas
@dataclass
class SearchReq:
    type: Optional[str] = None
    status: Optional[str] = None
    name: Optional[str] = None

@dataclass
class FavoriteReq:
    userId: str
    petId: int

@dataclass
class RecommendReq:
    userId: str
    preferences: Dict[str, Optional[str]]

@dataclass
class AddPetReq:
    id: int
    name: str
    type: Optional[str] = None
    status: Optional[str] = "available"
    photoUrls: Optional[List[str]] = None

# In-memory cache for favorites: {userId: set(petId)}
favorites_cache: Dict[str, set] = {}

PETSTORE_API_BASE = "https://petstore.swagger.io/v2"


# --- Workflow functions ---

async def process_pet(entity: dict):
    """
    Workflow: enrich pet entity before persistence and handle side effects.
    """
    logger.info(f"Workflow process_pet invoked for entity: {entity}")

    # Set creation timestamp if missing
    if "created_at" not in entity:
        entity["created_at"] = datetime.utcnow().isoformat()

    # Normalize type to lowercase
    if entity.get("type"):
        entity["type"] = entity["type"].lower()

    # Additional validation example: enforce status is one of allowed values
    allowed_statuses = {"available", "pending", "sold"}
    if "status" in entity and entity["status"] not in allowed_statuses:
        logger.warning(f"Invalid status '{entity['status']}' set to 'available'")
        entity["status"] = "available"

async def process_search(entity: dict):
    """
    Workflow: fetch pets from external API based on search parameters and store results.
    The 'entity' here represents search parameters.
    """
    logger.info(f"Workflow process_search invoked with search params: {entity}")

    type_ = entity.get("type")
    status = entity.get("status") or "available"
    name = entity.get("name")

    async with httpx.AsyncClient(timeout=10) as client:
        try:
            r = await client.get(f"{PETSTORE_API_BASE}/pet/findByStatus", params={"status": status})
            r.raise_for_status()
            pets = r.json()
        except Exception as e:
            logger.exception("Error fetching pets in process_search")
            entity['results'] = []
            return

    filtered = []
    for pet in pets:
        if type_:
            cat = pet.get("category", {}).get("name")
            if not cat or cat.lower() != type_.lower():
                continue
        if name and pet.get("name"):
            if name.lower() not in pet["name"].lower():
                continue
        filtered.append({
            "id": pet.get("id"),
            "name": pet.get("name"),
            "type": pet.get("category", {}).get("name", ""),
            "status": status,
            "photoUrls": pet.get("photoUrls", [])
        })

    entity['results'] = filtered

async def process_favorite(entity: dict):
    """
    Workflow for adding favorite pet to user cache.
    """
    logger.info(f"Workflow process_favorite invoked with data: {entity}")
    user_id = entity["userId"]
    pet_id = entity["petId"]
    user_favs = favorites_cache.setdefault(user_id, set())
    user_favs.add(pet_id)

async def process_recommend(entity: dict):
    """
    Workflow to fetch recommended pets for user excluding favorites.
    Store recommendations in entity['recommendations'].
    """
    logger.info(f"Workflow process_recommend invoked with data: {entity}")

    user_id = entity["userId"]
    prefs = entity.get("preferences") or {}
    type_ = prefs.get("type")
    status = prefs.get("status") or "available"

    async with httpx.AsyncClient(timeout=10) as client:
        try:
            r = await client.get(f"{PETSTORE_API_BASE}/pet/findByStatus", params={"status": status})
            r.raise_for_status()
            pets = r.json()
        except Exception as e:
            logger.exception("Error fetching pets in process_recommend")
            entity['recommendations'] = []
            return

    user_favs = favorites_cache.get(user_id, set())
    recommended = []
    for pet in pets:
        if pet.get("id") not in user_favs:
            if type_:
                cat = pet.get("category", {}).get("name")
                if not cat or cat.lower() != type_.lower():
                    continue
            recommended.append({
                "id": pet.get("id"),
                "name": pet.get("name"),
                "type": pet.get("category", {}).get("name", ""),
                "status": status,
                "photoUrls": pet.get("photoUrls", [])
            })
        if len(recommended) >= 5:
            break
    entity['recommendations'] = recommended

# --- End workflow functions ---


# --- Routes ---

@app.route("/pets/search", methods=["POST"])
@validate_request(SearchReq)
async def pets_search(data: SearchReq):
    entity = data.__dict__
    await process_search(entity)
    return jsonify({"pets": entity.get("results", [])})

@app.route("/pets/favorites", methods=["POST"])
@validate_request(FavoriteReq)
async def add_favorite(data: FavoriteReq):
    entity = data.__dict__
    await process_favorite(entity)
    return jsonify({"message": "Pet added to favorites"})

@app.route("/pets/favorites/<user_id>", methods=["GET"])
async def get_favorites(user_id: str):
    user_favs = favorites_cache.get(user_id, set())
    if not user_favs:
        return jsonify({"favorites": []})

    pets = []
    async with httpx.AsyncClient(timeout=10) as client:
        for pet_id in user_favs:
            try:
                r = await client.get(f"{PETSTORE_API_BASE}/pet/{pet_id}")
                if r.status_code == 200:
                    pet = r.json()
                    pets.append({
                        "id": pet.get("id"),
                        "name": pet.get("name"),
                        "type": pet.get("category", {}).get("name", ""),
                        "status": pet.get("status", "")
                    })
                else:
                    logger.info(f"Pet id {pet_id} not found")
            except Exception as e:
                logger.exception(e)
    return jsonify({"favorites": pets})

@app.route("/pets/recommend", methods=["POST"])
@validate_request(RecommendReq)
async def recommend_pets(data: RecommendReq):
    entity = data.__dict__
    await process_recommend(entity)
    return jsonify({"recommendations": entity.get("recommendations", [])})

@app.route("/pets/add", methods=["POST"])
@validate_request(AddPetReq)
async def add_pet(data: AddPetReq):
    entity = data.__dict__
    try:
        entity_id = await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model="pet",
            entity_version=ENTITY_VERSION,
            entity=entity
        )
        return jsonify({"message": "Pet added", "entity_id": entity_id})
    except Exception as e:
        logger.exception("Failed to add pet entity")
        return jsonify({"error": str(e)}), 500

# --- End routes ---

if __name__ == '__main__':
    import sys
    logging.basicConfig(stream=sys.stdout, level=logging.INFO)
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
