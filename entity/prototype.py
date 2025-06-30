import asyncio
import logging
from datetime import datetime
from typing import Dict
from dataclasses import dataclass
import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request  # validate_querystring not needed for current GET routes

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

@dataclass
class EntityRequest:
    job_id: str
    user_id: int

# In-memory async-safe cache for entity jobs keyed by job_id
class EntityJobCache:
    def __init__(self):
        self._lock = asyncio.Lock()
        self._cache: Dict[str, Dict] = {}

    async def set(self, job_id: str, value: Dict):
        async with self._lock:
            self._cache[job_id] = value

    async def get(self, job_id: str) -> Dict:
        async with self._lock:
            return self._cache.get(job_id)

    async def update_status(self, job_id: str, status: str):
        async with self._lock:
            if job_id in self._cache:
                self._cache[job_id]["status"] = status

entity_job_cache = EntityJobCache()

async def fetch_user_data(user_id: int) -> Dict:
    url = f"https://jsonplaceholder.typicode.com/users/{user_id}"
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        response.raise_for_status()
        return response.json()

async def fetch_user_posts(user_id: int) -> Dict:
    url = "https://jsonplaceholder.typicode.com/posts"
    params = {"userId": user_id}
    async with httpx.AsyncClient() as client:
        response = await client.get(url, params=params)
        response.raise_for_status()
        return response.json()

async def process_entity(entity_job_cache: EntityJobCache, job_id: str, data: Dict):
    try:
        logger.info(f"Processing entity job {job_id} with data: {data}")
        user_id = data.get("user_id")
        if not user_id:
            raise ValueError("Missing required field 'user_id' in data")
        user_info = await fetch_user_data(user_id)
        user_posts = await fetch_user_posts(user_id)
        # TODO: Add more complex workflow steps or calculations here if specified
        result = {
            "user": user_info,
            "posts": user_posts,
            "processedAt": datetime.utcnow().isoformat() + "Z",
        }
        await entity_job_cache.set(job_id, {"status": "completed", "result": result, "requestedAt": data.get("requestedAt")})
        logger.info(f"Entity job {job_id} completed successfully")
    except Exception as e:
        logger.exception(f"Error processing entity job {job_id}: {e}")
        await entity_job_cache.set(job_id, {"status": "failed", "error": str(e), "requestedAt": data.get("requestedAt")})

@app.route("/entity/<string:job_id>", methods=["GET"])
async def get_entity_job_status(job_id):
    job = await entity_job_cache.get(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404
    return jsonify(job)

@app.route("/entity", methods=["POST"])
@validate_request(EntityRequest)  # validation last for POST (workaround for quart-schema issue)
async def create_entity_job(data: EntityRequest):
    job_id = data.job_id
    user_id = data.user_id
    requested_at = datetime.utcnow().isoformat() + "Z"
    await entity_job_cache.set(job_id, {"status": "processing", "requestedAt": requested_at})
    asyncio.create_task(process_entity(entity_job_cache, job_id, {"user_id": user_id, "requestedAt": requested_at}))
    return jsonify({"job_id": job_id, "status": "processing", "requestedAt": requested_at}), 202

if __name__ == "__main__":
    app.run(use_reloader=False, debug=True, host="0.0.0.0", port=8000, threaded=True)