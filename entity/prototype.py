import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request, validate_querystring
from dataclasses import dataclass

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# Data classes for request validation
@dataclass
class FetchPetsRequest:
    type: str
    status: str
    limit: Optional[int] = None

@dataclass
class Preferences:
    type: str
    status: str
    maxResults: int

@dataclass
class MatchRequest:
    preferences: Preferences

# In-memory "cache" for fetched pets and matches keyed by job_id
pets_cache: Dict[str, List[Dict]] = {}
matches_cache: Dict[str, List[Dict]] = {}

async def fetch_pets_from_petstore(pet_type: str, status: str, limit: Optional[int]) -> List[Dict]:
    url = "https://petstore3.swagger.io/api/v3/pet/findByStatus"
    params = {"status": status} if status != "all" else {"status": "available"}
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(url, params=params, timeout=10)
            resp.raise_for_status()
            pets = resp.json()
        except Exception as e:
            logger.exception(f"Failed to fetch pets: {e}")
            return []
    def pet_matches_type(pet):
        if pet_type == "all":
            return True
        cat = pet.get("category")
        if not cat:
            return False
        if isinstance(cat, dict):
            return cat.get("name", "").lower() == pet_type.lower()
        return False
    filtered = [p for p in pets if pet_matches_type(p)]
    if limit and limit > 0:
        filtered = filtered[:limit]
    normalized = []
    for pet in filtered:
        normalized.append({
            "id": pet.get("id"),
            "name": pet.get("name"),
            "type": pet.get("category", {}).get("name") if isinstance(pet.get("category"), dict) else None,
            "status": status,
            "photoUrls": pet.get("photoUrls", []),
        })
    return normalized

async def match_pets(preferences: Dict) -> List[Dict]:
    pet_type = preferences.get("type", "all")
    max_results = preferences.get("maxResults", 10)
    pets = await fetch_pets_from_petstore(pet_type, "available", max_results)
    for pet in pets:
        pet["matchScore"] = min(1.0, len(pet.get("name") or "") / 10)
    return pets

@app.route("/pets/fetch", methods=["POST"])
# Workaround: place validate_request last in POST due to quart-schema defect
@validate_request(FetchPetsRequest)
async def pets_fetch(data: FetchPetsRequest):
    requested_at = datetime.utcnow().isoformat()
    job_id = f"fetch-{requested_at}"
    logger.info(f"Fetch request: {data}")
    async def process_fetch():
        pets = await fetch_pets_from_petstore(data.type, data.status, data.limit)
        pets_cache[job_id] = pets
        logger.info(f"Fetch job {job_id} done: {len(pets)} pets")
    asyncio.create_task(process_fetch())
    return jsonify({"jobId": job_id, "status": "processing", "requestedAt": requested_at})

@app.route("/pets/match", methods=["POST"])
# Workaround: place validate_request last in POST due to quart-schema defect
@validate_request(MatchRequest)
async def pets_match(data: MatchRequest):
    requested_at = datetime.utcnow().isoformat()
    job_id = f"match-{requested_at}"
    logger.info(f"Match request: {data}")
    async def process_match():
        matches = await match_pets(data.preferences.__dict__)
        matches_cache[job_id] = matches
        logger.info(f"Match job {job_id} done: {len(matches)} matches")
    asyncio.create_task(process_match())
    return jsonify({"jobId": job_id, "status": "processing", "requestedAt": requested_at})

@app.route("/pets", methods=["GET"])
async def get_pets():
    all_pets = []
    for lst in pets_cache.values():
        all_pets.extend(lst)
    return jsonify(all_pets)

@app.route("/pets/<int:pet_id>", methods=["GET"])
async def get_pet_detail(pet_id: int):
    for lst in pets_cache.values():
        for pet in lst:
            if pet.get("id") == pet_id:
                detail = pet.copy()
                detail["description"] = f"A lovely {detail.get('type')} named {detail.get('name')}."
                return jsonify(detail)
    return jsonify({"error": "Pet not found"}), 404

if __name__ == '__main__':
    import sys
    logging.basicConfig(stream=sys.stdout,
                        format='%(asctime)s %(levelname)s %(message)s',
                        level=logging.INFO)
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)