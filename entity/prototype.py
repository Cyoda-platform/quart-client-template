```python
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, Optional

import httpx
from quart import Quart, request, jsonify
from quart_schema import QuartSchema

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# In-memory per-session cache simulated by dict keyed by session id (simple version)
# TODO: Replace with proper session-aware or persistent cache if needed.
pets_cache: Dict[str, Any] = {}
fun_fact_cache: Dict[str, str] = {}

PETSTORE_API_BASE = "https://petstore.swagger.io/v2"

# --- Helpers ---


def get_session_id() -> str:
    """
    Temporary session id placeholder from client IP + user-agent.
    TODO: Replace with real session management.
    """
    peer = request.remote_addr or "unknown"
    ua = request.headers.get("User-Agent", "unknown")
    return f"{peer}-{ua}"


async def fetch_pets_from_petstore(
    criteria: Dict[str, Any]
) -> Optional[list]:
    """
    Fetch pets from Petstore API based on criteria.
    We'll map criteria to Petstore API `/pet/findByStatus` or `/pet/findByTags`.
    Petstore API supports findByStatus and findByTags but not combined queries,
    so we'll combine results manually as a simple prototype.
    """
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            results = []
            # Use status filter if provided
            statuses = [criteria["status"]] if criteria.get("status") else ["available", "pending", "sold"]

            for status in statuses:
                r = await client.get(f"{PETSTORE_API_BASE}/pet/findByStatus", params={"status": status})
                r.raise_for_status()
                pets = r.json()
                results.extend(pets)

            # Filter by type if provided (Petstore API does not support type filtering)
            if criteria.get("type"):
                filtered = [p for p in results if p.get("category", {}).get("name", "").lower() == criteria["type"].lower()]
            else:
                filtered = results

            # Filter by tags if provided
            if criteria.get("tags"):
                tags_set = set(map(str.lower, criteria["tags"]))
                def has_tags(p):
                    pet_tags = p.get("tags") or []
                    pet_tags_lower = set(t.get("name", "").lower() for t in pet_tags)
                    return tags_set.intersection(pet_tags_lower)
                filtered = [p for p in filtered if has_tags(p)]

            # Map to simplified pet info
            pets_mapped = []
            for p in filtered:
                pets_mapped.append(
                    {
                        "id": p.get("id"),
                        "name": p.get("name"),
                        "type": p.get("category", {}).get("name"),
                        "status": p.get("status"),
                        "tags": [t.get("name") for t in p.get("tags") or []],
                    }
                )
            return pets_mapped
    except Exception as e:
        logger.exception("Error fetching pets from Petstore API")
        return None


async def fetch_random_pet_fact(category: Optional[str] = None) -> str:
    """
    Fetch a random pet fact.
    TODO: No real pet-fact API specified, using mock facts here.
    Optionally filter by category.
    """
    # Example mock facts
    cat_facts = [
        "Cats sleep 70% of their lives.",
        "A group of cats is called a clowder.",
        "Cats have five toes on their front paws, but only four toes on their back paws.",
    ]
    dog_facts = [
        "Dogs have about 1,700 taste buds.",
        "Dogs' sense of smell is about 40 times better than humans'.",
        "The Basenji dog is known as the 'barkless dog'.",
    ]
    general_facts = [
        "Pets can reduce stress and anxiety in humans.",
        "The world's smallest dog was a Chihuahua that weighed 1.3 pounds.",
        "Owning a pet can lower your blood pressure.",
    ]

    facts_pool = general_facts
    if category:
        if category.lower() == "cats":
            facts_pool = cat_facts
        elif category.lower() == "dogs":
            facts_pool = dog_facts

    import random

    return random.choice(facts_pool)


# --- Routes ---


@app.route("/pets/search", methods=["POST"])
async def pets_search():
    data = await request.get_json(force=True)
    session_id = get_session_id()
    logger.info(f"Received pets search request from session {session_id}: {data}")

    pets = await fetch_pets_from_petstore(data or {})

    if pets is None:
        return jsonify({"error": "Failed to fetch pets from external API"}), 502

    # Cache the result for GET retrieval
    pets_cache[session_id] = pets

    return jsonify({"pets": pets})


@app.route("/pets/fun-facts", methods=["POST"])
async def pets_fun_facts():
    data = await request.get_json(force=True) or {}
    category = data.get("category")
    session_id = get_session_id()
    logger.info(f"Received fun fact request from session {session_id} category={category}")

    fact = await fetch_random_pet_fact(category)

    # Cache for GET retrieval
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
```
