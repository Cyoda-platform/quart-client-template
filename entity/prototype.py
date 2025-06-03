from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any, List
import asyncio
import logging
import sys

import httpx
from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request, validate_querystring

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# Data models
@dataclass
class PetSearch:
    type: str = None
    status: str = None
    limit: int = None

@dataclass
class FunFactsRequest:
    types: List[str]

# In-memory async-safe cache
class AsyncCache:
    def __init__(self):
        self._lock = asyncio.Lock()
        self._storage: Dict[str, Any] = {}

    async def get(self, key: str):
        async with self._lock:
            return self._storage.get(key)

    async def set(self, key: str, value: Any):
        async with self._lock:
            self._storage[key] = value

pets_cache = AsyncCache()
fun_facts_cache = AsyncCache()

PETSTORE_API_BASE = "https://petstore.swagger.io/v2"

async def fetch_pets_from_petstore(search_params: Dict[str, Any]) -> List[Dict[str, Any]]:
    status = search_params.get("status", "available")
    limit = search_params.get("limit", 20)
    pet_type = search_params.get("type", None)
    url = f"{PETSTORE_API_BASE}/pet/findByStatus"
    params = {"status": status}
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(url, params=params, timeout=10)
            resp.raise_for_status()
            pets = resp.json()
        except Exception as e:
            logger.exception(e)
            return []
    if pet_type:
        pets = [p for p in pets if p.get("category", {}).get("name", "").lower() == pet_type.lower()]
    return pets[:limit]

def generate_fun_facts(types: List[str]) -> List[str]:
    facts_db = {
        "cat": [
            "Cats sleep 70% of their lives.",
            "Cats have five toes on their front paws, but only four on the back ones."
        ],
        "dog": [
            "Dogs have three eyelids.",
            "Dogs sweat through their paws."
        ],
        "bird": [
            "Some birds can recognize themselves in a mirror.",
            "Birds have hollow bones to help them fly."
        ],
    }
    facts = []
    for t in types:
        facts.extend(facts_db.get(t.lower(), [f"No fun facts available for {t}."]))
    return facts if facts else ["No fun facts available."]

@app.route("/pets/search", methods=["POST"])
@validate_request(PetSearch)  # workaround: validation must come last for POST due to quart-schema issue
async def post_pets_search(data: PetSearch):
    requested_at = datetime.utcnow().isoformat()
    async def process_search():
        pets = await fetch_pets_from_petstore(data.__dict__)
        await pets_cache.set("last_search", pets)
        logger.info(f"Pets search processed at {requested_at} with params {data}")
    asyncio.create_task(process_search())
    return jsonify({"status": "processing", "requestedAt": requested_at}), 202

@app.route("/pets", methods=["GET"])
async def get_pets():
    pets = await pets_cache.get("last_search")
    if pets is None:
        return jsonify({"pets": [], "message": "No search results found yet."}), 200
    formatted = [
        {
            "id": p.get("id"),
            "name": p.get("name"),
            "type": p.get("category", {}).get("name", ""),
            "status": p.get("status"),
            "photoUrls": p.get("photoUrls", []),
        }
        for p in pets
    ]
    return jsonify({"pets": formatted})

@app.route("/pets/fun-facts", methods=["POST"])
@validate_request(FunFactsRequest)  # workaround: validation must come last for POST due to quart-schema issue
async def post_fun_facts(data: FunFactsRequest):
    requested_at = datetime.utcnow().isoformat()
    async def process_facts():
        facts = generate_fun_facts(data.types)
        await fun_facts_cache.set("last_facts", facts)
        logger.info(f"Fun facts generated at {requested_at} for types {data.types}")
    asyncio.create_task(process_facts())
    return jsonify({"status": "processing", "requestedAt": requested_at}), 202

@app.route("/pets/fun-facts", methods=["GET"])
async def get_fun_facts():
    facts = await fun_facts_cache.get("last_facts")
    if facts is None:
        return jsonify({"facts": [], "message": "No fun facts generated yet."}), 200
    return jsonify({"facts": facts})

if __name__ == '__main__':
    logging.basicConfig(
        format='[%(asctime)s] %(levelname)s in %(module)s: %(message)s',
        level=logging.INFO,
        stream=sys.stdout,
    )
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)