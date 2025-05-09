```python
import asyncio
import logging
from datetime import datetime
from typing import Optional

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# In-memory local cache to mock persistence
entity_job = {}
app_result = {"greeting": "Hello World"}  # default greeting


async def fetch_external_greeting(name: Optional[str]) -> str:
    """
    Example of a real external API call to get a greeting or related data.
    Using https://api.agify.io to get an estimated age by name as a demonstration.
    This is just to simulate external data retrieval and processing.
    """
    if not name:
        return "Hello World"

    url = f"https://api.agify.io/?name={name}"
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            # Example of using the external data for greeting personalization
            age = data.get("age")
            if age:
                return f"Hello {name}, you are approximately {age} years old"
            else:
                return f"Hello {name}"
    except Exception as e:
        logger.exception(e)
        # Fallback greeting on error
        return f"Hello {name}"


async def process_entity(job_id: str, data: dict):
    """
    Asynchronous processing of the POST request data.
    Simulates business logic, external API calls, calculations, etc.
    """
    try:
        name = data.get("name")
        greeting = await fetch_external_greeting(name)
        app_result["greeting"] = greeting

        # Update job status
        entity_job[job_id]["status"] = "completed"
        entity_job[job_id]["completedAt"] = datetime.utcnow().isoformat()
    except Exception as e:
        logger.exception(e)
        entity_job[job_id]["status"] = "failed"
        entity_job[job_id]["error"] = str(e)


@app.route("/hello", methods=["POST"])
async def post_hello():
    data = await request.get_json(force=True, silent=True) or {}
    job_id = str(len(entity_job) + 1)
    requested_at = datetime.utcnow().isoformat()
    entity_job[job_id] = {"status": "processing", "requestedAt": requested_at}

    # Fire and forget the processing task
    asyncio.create_task(process_entity(job_id, data))

    return jsonify({"status": "success", "message": "Hello World processed", "job_id": job_id})


@app.route("/hello", methods=["GET"])
async def get_hello():
    # Simply return the current greeting stored in app_result
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
```
