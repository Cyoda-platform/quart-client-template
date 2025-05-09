from dataclasses import dataclass
from typing import Optional, Dict
import asyncio
import logging
from datetime import datetime

import httpx
from quart import Quart, jsonify, request
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

user_tokens: Dict[str, str] = {}

CAT_API_BASE_URL = "https://api.thecatapi.com/v1"
CAT_FACTS_API_URL = "https://catfact.ninja/facts"
CAT_API_KEY = None  # Add your API key here if available

@dataclass
class RandomCatsRequest:
    category: Optional[str] = None
    limit: Optional[int] = 1

@dataclass
class SearchCatsRequest:
    breed_id: str
    limit: Optional[int] = 5

@dataclass
class CatFactsRequest:
    count: Optional[int] = 1

@dataclass
class AddFavoriteRequest:
    image_id: str

@dataclass
class AuthLoginRequest:
    username: str
    password: str

def make_auth_headers() -> dict:
    headers = {}
    if CAT_API_KEY:
        headers['x-api-key'] = CAT_API_KEY
    return headers

def generate_mock_token(username: str) -> str:
    return f"token-{username}"

def verify_token(token: str) -> Optional[str]:
    for user, t in user_tokens.items():
        if t == token:
            return user
    return None

async def process_user_favorite(entity_data: dict) -> dict:
    if "created_at" not in entity_data:
        entity_data["created_at"] = datetime.utcnow().isoformat()

    if not entity_data.get("url"):
        image_id = entity_data.get("image_id")
        if image_id:
            entity_data["url"] = f"https://placekitten.com/400/300?u={image_id}"

    image_id = entity_data.get("image_id")
    if image_id:
        metadata_entity = {
            "image_id": image_id,
            "source": "user_favorite_upload",
            "timestamp": datetime.utcnow().isoformat(),
        }
        try:
            await entity_service.add_item(
                token=cyoda_auth_service,
                entity_model="cat_image_metadata",
                entity_version=ENTITY_VERSION,
                entity=metadata_entity
            )
        except Exception as e:
            logger.warning(f"Failed to add supplementary cat_image_metadata entity: {e}")

    return entity_data

@app.route("/cats/random", methods=["POST"])
@validate_request(RandomCatsRequest)
async def fetch_random_cats(data: RandomCatsRequest):
    category = data.category
    limit = data.limit or 1
    params = {"limit": limit}
    if category:
        params["category_ids"] = category

    headers = make_auth_headers()
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(f"{CAT_API_BASE_URL}/images/search", params=params, headers=headers)
            resp.raise_for_status()
            images = resp.json()
            out_images = []
            for img in images:
                out_images.append({
                    "id": img.get("id"),
                    "url": img.get("url"),
                    "breeds": [b.get("name") for b in img.get("breeds", [])] if img.get("breeds") else [],
                    "metadata": {k: v for k, v in img.items() if k not in ("id", "url", "breeds")}
                })
            return jsonify({"images": out_images})
        except Exception as e:
            logger.exception(e)
            return jsonify({"error": "Failed to fetch random cats"}), 500

@app.route("/cats/search", methods=["POST"])
@validate_request(SearchCatsRequest)
async def search_cats_by_breed(data: SearchCatsRequest):
    breed_id = data.breed_id
    limit = data.limit or 5
    headers = make_auth_headers()
    async with httpx.AsyncClient() as client:
        try:
            resp_breeds = await client.get(f"{CAT_API_BASE_URL}/breeds/{breed_id}", headers=headers)
            if resp_breeds.status_code == 404:
                return jsonify({"error": "Breed not found"}), 404
            resp_breeds.raise_for_status()
            breed_info = resp_breeds.json()

            params = {"breed_id": breed_id, "limit": limit}
            resp_images = await client.get(f"{CAT_API_BASE_URL}/images/search", params=params, headers=headers)
            resp_images.raise_for_status()
            images = resp_images.json()
            out_images = [{"id": img.get("id"), "url": img.get("url")} for img in images]

            out_breed_info = {
                "id": breed_info.get("id"),
                "name": breed_info.get("name"),
                "description": breed_info.get("description"),
                "temperament": breed_info.get("temperament"),
            }

            return jsonify({"breed_info": out_breed_info, "images": out_images})
        except Exception as e:
            logger.exception(e)
            return jsonify({"error": "Failed to search cats by breed"}), 500

@app.route("/cats/facts", methods=["POST"])
@validate_request(CatFactsRequest)
async def get_cat_facts(data: CatFactsRequest):
    count = data.count or 1
    count = max(1, min(count, 10))

    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(CAT_FACTS_API_URL, params={"limit": count})
            resp.raise_for_status()
            facts_data = resp.json()
            facts = [f.get("fact") for f in facts_data.get("data", [])]
            return jsonify({"facts": facts})
        except Exception as e:
            logger.exception(e)
            return jsonify({"error": "Failed to fetch cat facts"}), 500

@app.route("/cats/upload", methods=["POST"])
async def upload_cat_image():
    auth_header = request.headers.get("Authorization", "")
    token = auth_header.replace("Bearer ", "")
    user = verify_token(token)
    if not user:
        return jsonify({"error": "Unauthorized"}), 401

    image_file = (await request.files).get("image_file")
    metadata_raw = (await request.form).get("metadata")

    metadata = {}
    if metadata_raw:
        import json
        try:
            metadata = json.loads(metadata_raw)
        except Exception:
            pass

    if not image_file:
        return jsonify({"error": "No image file provided"}), 400

    fake_image_id = f"uploaded-{datetime.utcnow().timestamp()}"

    favorite_data = {
        "user": user,
        "image_id": fake_image_id,
        "metadata": metadata
    }

    try:
        favorite_id = await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model="user_favorite",
            entity_version=ENTITY_VERSION,
            entity=favorite_data,
            workflow=process_user_favorite
        )
        return jsonify({
            "upload_status": "success",
            "image_id": fake_image_id,
            "message": "Image uploaded (mocked)",
            "favorite_id": favorite_id
        })
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to save favorite"}), 500

@app.route("/users/favorites", methods=["POST"])
@validate_request(AddFavoriteRequest)
async def add_favorite_cat(data: AddFavoriteRequest):
    auth_header = request.headers.get("Authorization", "")
    token = auth_header.replace("Bearer ", "")
    user = verify_token(token)
    if not user:
        return jsonify({"error": "Unauthorized"}), 401

    image_id = data.image_id

    try:
        condition = {"user": user}
        favorites = await entity_service.get_items_by_condition(
            token=cyoda_auth_service,
            entity_model="user_favorite",
            entity_version=ENTITY_VERSION,
            condition=condition
        )
        if any(fav.get("image_id") == image_id for fav in favorites):
            return jsonify({"status": "failure", "message": "Image already in favorites"}), 400

        favorite = {
            "user": user,
            "image_id": image_id,
            "metadata": {}
        }
        favorite_id = await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model="user_favorite",
            entity_version=ENTITY_VERSION,
            entity=favorite,
            workflow=process_user_favorite
        )
        return jsonify({"status": "success", "message": "Added to favorites", "favorite_id": favorite_id})
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to add favorite"}), 500

@app.route("/users/favorites", methods=["GET"])
async def get_user_favorites():
    auth_header = request.headers.get("Authorization", "")
    token = auth_header.replace("Bearer ", "")
    user = verify_token(token)
    if not user:
        return jsonify({"error": "Unauthorized"}), 401

    try:
        condition = {"user": user}
        favorites = await entity_service.get_items_by_condition(
            token=cyoda_auth_service,
            entity_model="user_favorite",
            entity_version=ENTITY_VERSION,
            condition=condition
        )
        return jsonify({"favorites": favorites})
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to retrieve favorites"}), 500

@app.route("/auth/login", methods=["POST"])
@validate_request(AuthLoginRequest)
async def login(data: AuthLoginRequest):
    username = data.username
    password = data.password

    if not username or not password:
        return jsonify({"error": "username and password required"}), 400

    token = generate_mock_token(username)
    user_tokens[username] = token

    return jsonify({"token": token, "expires_in": 3600})

if __name__ == "__main__":
    app.run(use_reloader=False, debug=True, host="0.0.0.0", port=8000, threaded=True)