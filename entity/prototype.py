from dataclasses import dataclass
from typing import List, Optional
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, Optional as Opt
import httpx
from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request  # validate_querystring imported but not used (no GET params)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

@dataclass
class PetSearch:
    type: Optional[str] = None
    status: Optional[str] = None
    tags: Optional[List[str]] = None

@dataclass
class FunFactRequest:
    category: Optional[str] = None

pets_cache: Dict[str, Any] = {}
fun_fact_cache: Dict[str, str] = {}
PETSTORE_API_BASE = "https://petstore.swagger.io/v2"

def get_session_id() -> str:
    peer = request.remote_addr or "unknown"
    ua = request.headers.get("User-Agent", "unknown")
    return f"{peer}-{ua}"

async def fetch_pets_from_petstore(criteria: Dict[str, Any]) -> Opt[list]:
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            results = []
            statuses = [criteria["status"]] if criteria.get("status") else ["available", "pending", "sold"]
            for status in statuses:
                r = await client.get(f"{PETSTORE_API_BASE}/pet/findByStatus", params={"status": status})
                r.raise_for_status()
                pets = r.json()
                results.extend(pets)
            if criteria.get("type"):
                filtered = [p for p in results if p.get("category", {}).get("name", "").lower() == criteria["type"].lower()]
            else:
                filtered = results
            if criteria.get("tags"):
                tags_set = set(map(str.lower, criteria["tags"]))
                def has_tags(p):
                    pet_tags = p.get("tags") or []
                    pet_tags_lower = set(t.get("name", "").lower() for t in pet_tags)
                    return tags_set.intersection(pet_tags_lower)
                filtered = [p for p in filtered if has_tags(p)]
            pets_mapped = []
            for p in filtered:
                pets_mapped.append({
                    "id": p.get("id"),
                    "name": p.get("name"),
                    "type": p.get("category", {}).get("name"),
                    "status": p.get("status"),
                    "tags": [t.get("name") for t in p.get("tags") or []],
                })
            return pets_mapped
    except Exception as e:
        logger.exception("Error fetching pets from Petstore API")
        return None

async def fetch_random_pet_fact(category: Opt[str] = None) -> str:
    cat_facts = ["Cats sleep 70% of their lives.", "A group of cats is called a clowder.", "Cats have five toes on their front paws, but only four toes on their back paws."]
    dog_facts = ["Dogs have about 1,700 taste buds.", "Dogs' sense of smell is about 40 times better than humans'.", "The Basenji dog is known as the 'barkless dog'."]
    general_facts = ["Pets can reduce stress and anxiety in humans.", "The world's smallest dog was a Chihuahua that weighed 1.3 pounds.", "Owning a pet can lower your blood pressure."]
    facts_pool = general_facts
    if category:
        if category.lower() == "cats":
            facts_pool = cat_facts
        elif category.lower() == "dogs":
            facts_pool = dog_facts
    import random
    return random.choice(facts_pool)

@app.route("/pets/search", methods=["POST"])
# TODO: validate_request must be last decorator on POST due to quart-schema workaround
@validate_request(PetSearch)
async def pets_search(data: PetSearch):
    session_id = get_session_id()
    logger.info(f"Received pets search request from session {session_id}: {data}")
    pets = await fetch_pets_from_petstore(data.__dict__)
    if pets is None:
        return jsonify({"error": "Failed to fetch pets from external API"}), 502
    pets_cache[session_id] = pets
    return jsonify({"pets": pets})

@app.route("/pets/fun-facts", methods=["POST"])
# TODO: validate_request must be last decorator on POST due to quart-schema workaround
@validate_request(FunFactRequest)
async def pets_fun_facts(data: FunFactRequest):
    session_id = get_session_id()
    logger.info(f"Received fun fact request from session {session_id} category={data.category}")
    fact = await fetch_random_pet_fact(data.category)
    fun_fact_cache[session_id] = fact
    return jsonify({"fact": fact})

@app.route("/pets", methods=["GET"])
async def pets_get():
    session_id = get_session_id()
    pets = pets_cache.get(session_id, [])
    logger.info(f"Returning cached pets for session {session_id}")
    return jsonify({"pets": pets})

@app.route("/pets/fun-fact", methods=["GET"])
async def pets_fun_fact_get():
    session_id = get_session_id()
    fact = fun_fact_cache.get(session_id, "")
    logger.info(f"Returning cached fun fact for session {session_id}")
    return jsonify({"fact": fact})

if __name__ == "__main__":
    app.run(use_reloader=False, debug=True, host="0.0.0.0", port=8000, threaded=True)