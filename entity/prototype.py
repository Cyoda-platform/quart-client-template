```python
import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# ----------------------------
# In-memory mock storage/cache
# ----------------------------
user_favorites: Dict[str, List[Dict]] = {}  # user_token -> list of favorites (image dict)
user_tokens: Dict[str, str] = {}  # username -> token (mock)
entity_jobs: Dict[str, Dict] = {}  # job_id -> status dict for async jobs (if needed)

# ----------------------------
# Constants for external APIs
# ----------------------------
CAT_API_BASE_URL = "https://api.thecatapi.com/v1"
CAT_FACTS_API_URL = "https://catfact.ninja/facts"

# TODO: If you have an API key from TheCatAPI, put here.
CAT_API_KEY = None  # e.g. 'your_api_key_here'


# ----------------------------
# Utility functions
# ----------------------------

def make_auth_headers() -> Dict[str, str]:
    headers = {}
    if CAT_API_KEY:
        headers['x-api-key'] = CAT_API_KEY
    return headers


def generate_mock_token(username: str) -> str:
    # TODO: Replace with real token generation
    return f"token-{username}"


def verify_token(token: str) -> Optional[str]:
    # Mock token verification: reverse lookup
    for user, t in user_tokens.items():
        if t == token:
            return user
    return None


# ----------------------------
# Routes
# ----------------------------

@app.route("/cats/random", methods=["POST"])
async def fetch_random_cats():
    """
    POST /cats/random
    Request JSON: { category?: str, limit?: int }
    Response: { images: [ {id, url, breeds[], metadata} ] }
    """
    data = await request.get_json(force=True)
    category = data.get("category")
    limit = data.get("limit", 1)
    params = {"limit": limit}
    if category:
        params["category_ids"] = category  # Cat API uses category_ids

    headers = make_auth_headers()
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(f"{CAT_API_BASE_URL}/images/search", params=params, headers=headers)
            resp.raise_for_status()
            images = resp.json()
            # Normalize output
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
async def search_cats_by_breed():
    """
    POST /cats/search
    Request JSON: { breed_id: str, limit?: int }
    Response: { breed_info: {...}, images: [ {id, url} ] }
    """
    data = await request.get_json(force=True)
    breed_id = data.get("breed_id")
    limit = data.get("limit", 5)
    if not breed_id:
        return jsonify({"error": "breed_id is required"}), 400

    headers = make_auth_headers()
    async with httpx.AsyncClient() as client:
        try:
            # Get breed info
            resp_breeds = await client.get(f"{CAT_API_BASE_URL}/breeds/{breed_id}", headers=headers)
            if resp_breeds.status_code == 404:
                return jsonify({"error": "Breed not found"}), 404
            resp_breeds.raise_for_status()
            breed_info = resp_breeds.json()

            # Get images by breed
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
async def get_cat_facts():
    """
    POST /cats/facts
    Request JSON: { count?: int }
    Response: { facts: [string] }
    """
    data = await request.get_json(force=True)
    count = data.get("count", 1)
    count = max(1, min(count, 10))  # limit count 1-10 to avoid abuse

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
    """
    POST /cats/upload
    Upload cat image with metadata (requires auth)
    TODO: This is a placeholder - TheCatAPI requires API key and specific process for uploads.
    """
    # Authentication check
    auth_header = request.headers.get("Authorization", "")
    token = auth_header.replace("Bearer ", "")
    user = verify_token(token)
    if not user:
        return jsonify({"error": "Unauthorized"}), 401

    # Retrieve file and metadata
    image_file = (await request.files).get("image_file")
    metadata_raw = (await request.form).get("metadata")
    # TODO: Parse metadata JSON if provided
    metadata = {}
    if metadata_raw:
        import json
        try:
            metadata = json.loads(metadata_raw)
        except Exception:
            pass

    if not image_file:
        return jsonify({"error": "No image file provided"}), 400

    # TODO: Implement real upload to TheCatAPI or other storage
    # For prototype, just mock success and store in user favorites with a fake id/url
    fake_image_id = f"uploaded-{datetime.utcnow().timestamp()}"
    fake_url = f"https://placekitten.com/400/300?u={fake_image_id}"

    # Save to user favorites as a placeholder for uploaded images
    user_favorites.setdefault(user, []).append({
        "image_id": fake_image_id,
        "url": fake_url,
        "metadata": metadata
    })

    return jsonify({
        "upload_status": "success",
        "image_id": fake_image_id,
        "message": "Image uploaded (mocked)"
    })


@app.route("/users/favorites", methods=["POST"])
async def add_favorite_cat():
    """
    POST /users/favorites
    Add a cat image to user's favorites (requires auth)
    Request JSON: { image_id: str }
    """
    auth_header = request.headers.get("Authorization", "")
    token = auth_header.replace("Bearer ", "")
    user = verify_token(token)
    if not user:
        return jsonify({"error": "Unauthorized"}), 401

    data = await request.get_json(force=True)
    image_id = data.get("image_id")
    if not image_id:
        return jsonify({"error": "image_id is required"}), 400

    # TODO: Normally verify image_id exists in CatAPI or uploads; here we mock
    # Just add a placeholder entry with image_id and dummy url
    favorite = {
        "image_id": image_id,
        "url": f"https://placekitten.com/400/300?u={image_id}",
        "metadata": {}
    }
    user_favorites.setdefault(user, [])

    # Avoid duplicates
    if any(fav["image_id"] == image_id for fav in user_favorites[user]):
        return jsonify({"status": "failure", "message": "Image already in favorites"}), 400

    user_favorites[user].append(favorite)
    return jsonify({"status": "success", "message": "Added to favorites"})


@app.route("/users/favorites", methods=["GET"])
async def get_user_favorites():
    """
    GET /users/favorites
    Retrieve user's favorite cat images (requires auth)
    """
    auth_header = request.headers.get("Authorization", "")
    token = auth_header.replace("Bearer ", "")
    user = verify_token(token)
    if not user:
        return jsonify({"error": "Unauthorized"}), 401

    favorites = user_favorites.get(user, [])
    return jsonify({"favorites": favorites})


@app.route("/auth/login", methods=["POST"])
async def login():
    """
    POST /auth/login
    Request JSON: { username: str, password: str }
    Response: { token: str, expires_in: int }
    """
    data = await request.get_json(force=True)
    username = data.get("username")
    password = data.get("password")

    # TODO: Replace with real user validation
    if not username or not password:
        return jsonify({"error": "username and password required"}), 400

    # Mock password check always succeeds
    token = generate_mock_token(username)
    user_tokens[username] = token

    # Mock expiration 1 hour (3600s)
    return jsonify({"token": token, "expires_in": 3600})


# ----------------------------
# Entry point
# ----------------------------

if __name__ == "__main__":
    app.run(use_reloader=False, debug=True, host="0.0.0.0", port=8000, threaded=True)
```
