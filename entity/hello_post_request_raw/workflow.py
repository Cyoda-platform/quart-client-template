from dataclasses import dataclass
from typing import Optional
import asyncio
import logging
from datetime import datetime
import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

@dataclass
class HelloPostRequest:
    name: Optional[str] = None  # optional string to personalize greeting

entity_job = {}
app_result = {"greeting": "Hello World"}  # default greeting

async def process_fetch_external_greeting(entity: dict):
    name = entity.get("name")
    if not name:
        entity["greeting"] = "Hello World"
        return
    url = f"https://api.agify.io/?name={name}"
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            age = data.get("age")
            if age:
                entity["greeting"] = f"Hello {name}, you are approximately {age} years old"
            else:
                entity["greeting"] = f"Hello {name}"
    except Exception as e:
        logger.exception(e)
        entity["greeting"] = f"Hello {name}"

async def process_entity(entity: dict):
    try:
        await process_fetch_external_greeting(entity)
        entity["status"] = "completed"
        entity["completedAt"] = datetime.utcnow().isoformat()
    except Exception as e:
        logger.exception(e)
        entity["status"] = "failed"
        entity["error"] = str(e)

async def process_hello_post_request_raw(entity: dict):
    entity["status"] = "processing"
    entity["requestedAt"] = datetime.utcnow().isoformat()
    asyncio.create_task(process_entity(entity))

@app.route("/hello", methods=["POST"])
@validate_request(HelloPostRequest)  # validation last in POST (workaround for quart-schema issue)
async def hello_post_request(data: HelloPostRequest):
    job_id = str(len(entity_job) + 1)
    entity = {"id": job_id, **data.__dict__}
    entity_job[job_id] = entity
    await process_hello_post_request_raw(entity)
    return jsonify({"status": "success", "message": "Hello World processed", "job_id": job_id})

@app.route("/hello", methods=["GET"])
async def hello_get_request():
    return jsonify({"greeting": app_result.get("greeting", "Hello World")})

if __name__ == '__main__':
    import sys
    import logging

    logging.basicConfig(
        stream=sys.stdout,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        level=logging.INFO,
    )

    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)