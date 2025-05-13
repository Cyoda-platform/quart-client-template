import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

import httpx
from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# Workaround: due to quart-schema defect, place @validate_request after @app.route for POST

@dataclass
class PetSearch:
    type: Optional[str] = None
    status: Optional[str] = None
    name: Optional[str] = None

@dataclass
class PetAdd:
    name: str
    type: str
    status: str
    photoUrls: Optional[List[str]] = None

@dataclass
class PetUpdate:
    id: int
    name: Optional[str] = None
    type: Optional[str] = None
    status: Optional[str] = None
    photoUrls: Optional[List[str]] = None

@dataclass
class PetDelete:
    id: int

pets_cache: Dict[int, Dict[str, Any]] = {}
entity_jobs: Dict[str, Dict[str, Any]] = {}

PETSTORE_API_BASE = "https://petstore.swagger.io/v2"

async def fetch_pet_from_external(pet_id: int) -> Dict[str, Any]:
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(f"{PETSTORE_API_BASE}/pet/{pet_id}")
            resp.raise_for_status()
            data = resp.json()
            pets_cache[pet_id] = data
            return data
        except httpx.HTTPStatusError as e:
            logger.exception(f"Pet not found in external API: {pet_id}")
            raise
        except Exception as e:
            logger.exception("Unexpected error fetching pet from external API")
            raise

async def process_search(criteria: Dict[str, Any]) -> None:
    job_id = criteria.get("job_id")
    try:
        async with httpx.AsyncClient() as client:
            status = criteria.get("status")
            type_ = criteria.get("type")
            name = criteria.get("name")
            pets = []
            if status:
                resp = await client.get(f"{PETSTORE_API_BASE}/pet/findByStatus", params={"status": status})
            else:
                resp = await client.get(f"{PETSTORE_API_BASE}/pet/findByStatus", params={"status": "available,pending,sold"})
            resp.raise_for_status()
            pets_data = resp.json()
            for pet in pets_data:
                if type_ and pet.get("category", {}).get("name", "").lower() != type_.lower():
                    continue
                if name and name.lower() not in pet.get("name", "").lower():
                    continue
                pets.append({
                    "id": pet["id"],
                    "name": pet.get("name"),
                    "type": pet.get("category", {}).get("name"),
                    "status": pet.get("status"),
                    "photoUrls": pet.get("photoUrls", []),
                })
            entity_jobs[job_id]["status"] = "completed"
            entity_jobs[job_id]["result"] = {"pets": pets}
            entity_jobs[job_id]["completedAt"] = datetime.utcnow().isoformat()
    except Exception as e:
        logger.exception("Error processing pet search")
        entity_jobs[job_id]["status"] = "failed"
        entity_jobs[job_id]["error"] = str(e)

async def process_add_pet(data: Dict[str, Any], job_id: str) -> None:
    try:
        async with httpx.AsyncClient() as client:
            payload = {
                "name": data.get("name"),
                "photoUrls": data.get("photoUrls", []),
                "status": data.get("status"),
                "category": {"name": data.get("type")} if data.get("type") else None,
                "id": None
            }
            if payload["category"] is None:
                payload.pop("category")
            resp = await client.post(f"{PETSTORE_API_BASE}/pet", json=payload)
            resp.raise_for_status()
            pet_resp = resp.json()
            pets_cache[pet_resp["id"]] = pet_resp
            entity_jobs[job_id]["status"] = "completed"
            entity_jobs[job_id]["result"] = {
                "id": pet_resp["id"],
                "message": "Pet added successfully"
            }
            entity_jobs[job_id]["completedAt"] = datetime.utcnow().isoformat()
    except Exception as e:
        logger.exception("Error adding pet")
        entity_jobs[job_id]["status"] = "failed"
        entity_jobs[job_id]["error"] = str(e)

async def process_update_pet(data: Dict[str, Any], job_id: str) -> None:
    try:
        pet_id = data.get("id")
        if pet_id is None:
            raise ValueError("Pet id is required for update")
        async with httpx.AsyncClient() as client:
            payload = {
                "id": pet_id,
                "name": data.get("name"),
                "photoUrls": data.get("photoUrls", []),
                "status": data.get("status"),
                "category": {"name": data.get("type")} if data.get("type") else None,
            }
            payload = {k: v for k, v in payload.items() if v is not None}
            if "category" in payload and payload["category"] is None:
                payload.pop("category")
            resp = await client.put(f"{PETSTORE_API_BASE}/pet", json=payload)
            resp.raise_for_status()
            pet_resp = resp.json()
            pets_cache[pet_id] = pet_resp
            entity_jobs[job_id]["status"] = "completed"
            entity_jobs[job_id]["result"] = {"message": "Pet updated successfully"}
            entity_jobs[job_id]["completedAt"] = datetime.utcnow().isoformat()
    except Exception as e:
        logger.exception("Error updating pet")
        entity_jobs[job_id]["status"] = "failed"
        entity_jobs[job_id]["error"] = str(e)

async def process_delete_pet(data: Dict[str, Any], job_id: str) -> None:
    try:
        pet_id = data.get("id")
        if pet_id is None:
            raise ValueError("Pet id is required for delete")
        async with httpx.AsyncClient() as client:
            resp = await client.delete(f"{PETSTORE_API_BASE}/pet/{pet_id}")
            resp.raise_for_status()
            pets_cache.pop(pet_id, None)
            entity_jobs[job_id]["status"] = "completed"
            entity_jobs[job_id]["result"] = {"message": "Pet deleted successfully"}
            entity_jobs[job_id]["completedAt"] = datetime.utcnow().isoformat()
    except Exception as e:
        logger.exception("Error deleting pet")
        entity_jobs[job_id]["status"] = "failed"
        entity_jobs[job_id]["error"] = str(e)

@app.route("/pets/search", methods=["POST"])
@validate_request(PetSearch)
async def pets_search(data: PetSearch):
    job_id = f"search_{datetime.utcnow().timestamp()}"
    entity_jobs[job_id] = {"status": "processing", "requestedAt": datetime.utcnow().isoformat()}
    criteria = data.__dict__.copy()
    criteria["job_id"] = job_id
    asyncio.create_task(process_search(criteria))
    return jsonify({"job_id": job_id}), 202

@app.route("/pets/add", methods=["POST"])
@validate_request(PetAdd)
async def pets_add(data: PetAdd):
    job_id = f"add_{datetime.utcnow().timestamp()}"
    entity_jobs[job_id] = {"status": "processing", "requestedAt": datetime.utcnow().isoformat()}
    payload = data.__dict__.copy()
    asyncio.create_task(process_add_pet(payload, job_id))
    return jsonify({"job_id": job_id}), 202

@app.route("/pets/update", methods=["POST"])
@validate_request(PetUpdate)
async def pets_update(data: PetUpdate):
    job_id = f"update_{datetime.utcnow().timestamp()}"
    entity_jobs[job_id] = {"status": "processing", "requestedAt": datetime.utcnow().isoformat()}
    payload = data.__dict__.copy()
    asyncio.create_task(process_update_pet(payload, job_id))
    return jsonify({"job_id": job_id}), 202

@app.route("/pets/delete", methods=["POST"])
@validate_request(PetDelete)
async def pets_delete(data: PetDelete):
    job_id = f"delete_{datetime.utcnow().timestamp()}"
    entity_jobs[job_id] = {"status": "processing", "requestedAt": datetime.utcnow().isoformat()}
    payload = data.__dict__.copy()
    asyncio.create_task(process_delete_pet(payload, job_id))
    return jsonify({"job_id": job_id}), 202

@app.route("/pets/job_status/<job_id>", methods=["GET"])
async def job_status(job_id: str):
    job = entity_jobs.get(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404
    return jsonify(job)

@app.route("/pets/<int:pet_id>", methods=["GET"])
async def get_pet(pet_id: int):
    pet = pets_cache.get(pet_id)
    if pet:
        return jsonify(pet)
    try:
        pet = await fetch_pet_from_external(pet_id)
        return jsonify(pet)
    except httpx.HTTPStatusError:
        return jsonify({"error": "Pet not found"}), 404
    except Exception:
        return jsonify({"error": "Failed to retrieve pet"}), 500

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)