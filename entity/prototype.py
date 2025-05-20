from dataclasses import dataclass
from typing import Optional, List, Dict, Any
import asyncio
import logging
from datetime import datetime

import httpx
from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# request models
@dataclass
class QueryFilters:
    status: Optional[str]
    category: Optional[str]
    tags: Optional[List[str]]

@dataclass
class PetIdRequest:
    id: int

# workaround: quart-schema defect requires validate_request after @app.route for POST
@app.route("/pets/query", methods=["POST"])
@validate_request(QueryFilters)
async def pets_query(data: QueryFilters):
    filters: Dict[str, Any] = {}
    if data.status is not None:
        filters["status"] = data.status
    if data.category is not None:
        filters["category"] = data.category
    if data.tags is not None:
        filters["tags"] = data.tags
    await asyncio.create_task(process_pets_query(filters))
    return jsonify({"status": "processing", "requestedAt": datetime.utcnow().isoformat()}), 202

@app.route("/pets", methods=["GET"])
async def get_pets():
    async with cache._pets_list_lock:
        if cache._pets_list is None:
            return jsonify({"error": "No pets data cached yet. Please POST /pets/query first."}), 404
        return jsonify(cache._pets_list)

@app.route("/pets/details", methods=["POST"])
@validate_request(PetIdRequest)
async def pet_details_post(data: PetIdRequest):
    pet_id = data.id
    await asyncio.create_task(process_pet_detail(pet_id))
    return jsonify({"status": "processing", "requestedAt": datetime.utcnow().isoformat(), "petId": pet_id}), 202

@app.route("/pets/details/<int:pet_id>", methods=["GET"])
async def pet_details_get(pet_id: int):
    async with cache._pets_details_lock:
        pet_detail = cache._pets_details.get(pet_id)
        if pet_detail is None:
            return jsonify({"error": f"No cached details for pet ID {pet_id}. Please POST /pets/details first."}), 404
        return jsonify(pet_detail)

# existing helper functions and cache setup remain unchanged
# ...
if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)