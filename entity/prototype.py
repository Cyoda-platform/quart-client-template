import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime

from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request, validate_querystring
import httpx

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# Request schema dataclass
@dataclass
class HelloRequest:
    name: str = None  # optional name for personalization

# In-memory cache to store last greeting message and jobs
class Cache:
    def __init__(self):
        self._lock = asyncio.Lock()
        self._data = {
            "last_greeting": None,
            "entity_job": {}
        }

    async def set_last_greeting(self, message: str):
        async with self._lock:
            self._data["last_greeting"] = message

    async def get_last_greeting(self):
        async with self._lock:
            return self._data["last_greeting"]

    async def add_job(self, job_id, job_data):
        async with self._lock:
            self._data["entity_job"][job_id] = job_data

cache = Cache()

async def fetch_external_greeting(name: str = None) -> str:
    async with httpx.AsyncClient() as client:
        try:
            if name:
                resp = await client.get("https://api.agify.io/", params={"name": name})
                resp.raise_for_status()
                data = resp.json()
                age = data.get("age")
                greeting = f"Hello, {name}!"
                if age:
                    greeting += f" I guess you are around {age} years old."
                return greeting
            else:
                return "Hello World"
        except Exception as e:
            logger.exception(e)
            return "Hello World"

async def process_entity(entity_job: dict, data: dict):
    job_id = data.get("job_id")
    name = data.get("name", None)
    try:
        greeting_msg = await fetch_external_greeting(name)
        await cache.set_last_greeting(greeting_msg)
        async with cache._lock:
            entity_job[job_id]["status"] = "completed"
            entity_job[job_id]["result"] = greeting_msg
            entity_job[job_id]["completedAt"] = datetime.utcnow().isoformat()
        logger.info(f"Job {job_id} completed with greeting: {greeting_msg}")
    except Exception as e:
        logger.exception(e)
        async with cache._lock:
            entity_job[job_id]["status"] = "failed"
            entity_job[job_id]["error"] = str(e)

@app.route("/hello", methods=["POST"])
@validate_request(HelloRequest)  # validation last for POST due to quart-schema defect workaround
async def post_hello(data: HelloRequest):
    job_id = datetime.utcnow().isoformat() + "-" + str(id(data))
    requested_at = datetime.utcnow().isoformat()

    job_data = {
        "status": "processing",
        "requestedAt": requested_at,
        "name": data.name
    }

    await cache.add_job(job_id, job_data)

    # Fire and forget processing task
    asyncio.create_task(process_entity(cache._data["entity_job"], {"job_id": job_id, "name": data.name}))

    return jsonify({"job_id": job_id, "status": "processing"}), 202

@app.route("/hello/result", methods=["GET"])
async def get_hello_result():
    last_greeting = await cache.get_last_greeting()
    if last_greeting is None:
        return jsonify({"message": "No greeting message available yet"}), 404
    return jsonify({"message": last_greeting})

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    app.run(use_reloader=False, debug=True, host="0.0.0.0", port=8000, threaded=True)