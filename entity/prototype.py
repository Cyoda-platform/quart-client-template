import asyncio
import logging
import uuid
from datetime import datetime
from typing import Dict, List
from dataclasses import dataclass

import httpx
from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request, validate_querystring

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# Data models for request validation
@dataclass
class PetSearch:
    type: str
    status: str
    tags: List[str]

@dataclass
class PetRecommendation:
    preferredType: str
    maxResults: int

# In-memory "cache" to mock persistence
search_cache: Dict[str, dict] = {}
rec_cache: Dict[str, dict] = {}

PETSTORE_API_BASE = "https://petstore.swagger.io/v2"

async def fetch_pets_from_petstore(params: dict) -> list:
    status = params.get("status") or "available"
    url = f"{PETSTORE_API_BASE}/pet/findByStatus"
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, params={"status": status})
            resp.raise_for_status()
            pets = resp.json()
            pet_type = params.get("type")
            tags = set(params.get("tags", []))
            filtered = []
            for pet in pets:
                pet_cat = pet.get("category", {}).get("name", "").lower()
                if pet_type and pet_type.lower() != pet_cat:
                    continue
                pet_tags = set(t.get("name", "").lower() for t in pet.get("tags", []))
                if tags and not tags.issubset(pet_tags):
                    continue
                filtered.append({
                    "id": pet.get("id"),
                    "name": pet.get("name"),
                    "status": pet.get("status"),
                    "tags": list(pet_tags)
                })
            return filtered
    except Exception as e:
        logger.exception(e)
        return []

async def generate_recommendations(preferred_type: str, max_results: int) -> list:
    try:
        pets = await fetch_pets_from_petstore({"status": "available", "type": preferred_type})
        recommendations = []
        for pet in pets[:max_results]:
            recommendations.append({
                "id": pet["id"],
                "name": pet["name"],
                "description": f"A lovely {preferred_type} looking for a home!"
            })
        while len(recommendations) < max_results:
            recommendations.append({
                "id": 0,
                "name": "Mystery Pet",
                "description": "A mysterious pet waiting to surprise you!"
            })
        return recommendations
    except Exception as e:
        logger.exception(e)
        return []

async def process_search_job(search_id: str, criteria: dict):
    try:
        pets = await fetch_pets_from_petstore(criteria)
        search_cache[search_id]["result"] = {
            "searchId": search_id,
            "count": len(pets),
            "pets": pets,
        }
        search_cache[search_id]["status"] = "completed"
    except Exception as e:
        logger.exception(e)
        search_cache[search_id]["status"] = "failed"

async def process_recommendation_job(rec_id: str, prefs: dict):
    try:
        recs = await generate_recommendations(prefs.get("preferredType", ""), prefs.get("maxResults", 3))
        rec_cache[rec_id]["result"] = {
            "recId": rec_id,
            "recommendations": recs,
        }
        rec_cache[rec_id]["status"] = "completed"
    except Exception as e:
        logger.exception(e)
        rec_cache[rec_id]["status"] = "failed"

@app.route("/pets/search", methods=["POST"])
# workaround: placing validate_request after route due to quart-schema defect
@validate_request(PetSearch)
async def pets_search(data: PetSearch):
    search_id = str(uuid.uuid4())
    requested_at = datetime.utcnow()
    search_cache[search_id] = {
        "status": "processing",
        "requestedAt": requested_at,
        "result": None,
    }
    asyncio.create_task(process_search_job(search_id, data.__dict__))
    return jsonify({"searchId": search_id, "status": "processing"}), 202

@app.route("/pets/search/<search_id>", methods=["GET"])
async def get_search_result(search_id):
    cached = search_cache.get(search_id)
    if not cached:
        return jsonify({"error": "searchId not found"}), 404
    if cached["status"] == "processing":
        return jsonify({"searchId": search_id, "status": "processing"}), 202
    if cached["status"] == "failed":
        return jsonify({"searchId": search_id, "status": "failed"}), 500
    return jsonify(cached["result"])

@app.route("/pets/recommendation", methods=["POST"])
# workaround: placing validate_request after route due to quart-schema defect
@validate_request(PetRecommendation)
async def pets_recommendation(data: PetRecommendation):
    rec_id = str(uuid.uuid4())
    requested_at = datetime.utcnow()
    rec_cache[rec_id] = {
        "status": "processing",
        "requestedAt": requested_at,
        "result": None,
    }
    asyncio.create_task(process_recommendation_job(rec_id, data.__dict__))
    return jsonify({"recId": rec_id, "status": "processing"}), 202

@app.route("/pets/recommendation/<rec_id>", methods=["GET"])
async def get_recommendation_result(rec_id):
    cached = rec_cache.get(rec_id)
    if not cached:
        return jsonify({"error": "recId not found"}), 404
    if cached["status"] == "processing":
        return jsonify({"recId": rec_id, "status": "processing"}), 202
    if cached["status"] == "failed":
        return jsonify({"recId": rec_id, "status": "failed"}), 500
    return jsonify(cached["result"])

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)