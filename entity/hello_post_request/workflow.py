from dataclasses import dataclass
from typing import Optional
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

async def fetch_external_greeting(name: Optional[str]) -> str:
    if not name:
        return "Hello World"
    url = f"https://api.agify.io/?name={name}"
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            age = data.get("age")
            if age:
                return f"Hello {name}, you are approximately {age} years old"
            else:
                return f"Hello {name}"
    except Exception as e:
        logger.exception(f"Error fetching external greeting: {e}")
        return f"Hello {name}"

async def process_set_initial_state(entity: dict):
    entity['status'] = 'processing'
    entity['requestedAt'] = datetime.utcnow().isoformat()

async def process_set_greeting(entity: dict):
    name = entity.get('name')
    greeting = await fetch_external_greeting(name)
    entity['greeting'] = greeting
    app_result['greeting'] = greeting  # update global app result

async def process_mark_completed(entity: dict):
    entity['status'] = 'completed'
    entity['completedAt'] = datetime.utcnow().isoformat()

async def process_mark_failed(entity: dict, error: Exception):
    logger.exception(f"Workflow processing error: {error}")
    entity['status'] = 'failed'
    entity['error'] = str(error)

@app.route("/hello", methods=["POST"])
@validate_request(HelloPostRequest)  # validation last in POST (workaround for quart-schema issue)
async def hello_post_request(data: HelloPostRequest):
    job_id = str(len(entity_job) + 1)
    entity = {"id": job_id, **data.__dict__}
    entity_job[job_id] = entity
    await process_hello_post_request(entity)
    return jsonify({"status": entity.get("status", "failed"), "message": "Hello World processed", "job_id": job_id})

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