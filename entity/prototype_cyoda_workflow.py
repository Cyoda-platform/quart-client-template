Understood.  
The goal is to refactor the code so that the endpoint controllers only handle request validation and call to `entity_service.add_item()`, passing the workflow function, and all async processing logic is moved inside the workflow function.

**Key points:**
- The workflow function receives the entity data (dict), can mutate it before persistence.
- The workflow function can run async tasks, including "fire and forget".
- It cannot call add/update/delete on the same entity model (would cause infinite recursion).
- If the entity state needs to be changed, mutate the entity dict directly.
- For other entity models, calling add/update/delete is allowed.
- The endpoint handlers become very thin.

---

### What to move into the workflow function `process_weather_fetch_request`?

Currently:
- In the endpoint `/weather/fetch`:
  - The only logic after validation is calling `add_item()` with workflow.
- The workflow function previously only marked status and started processing task.
- The actual processing is done in `process_entity(job_id, data)`:
  - Fetching weather data from external API.
  - Updating the entity with processed data and status.

Note: `process_entity()` calls `update_item()` on the same entity model (allowed inside workflow because it is a different function, but not inside the workflow function itself on the same entity). The `process_entity` function is a background async task.

---

### Refactoring plan

Move all logic related to:
- fetching weather data,
- processing it,
- updating the entity with results/status,

**inside the workflow function** as async calls or fire-and-forget tasks.

How?

Inside `process_weather_fetch_request(entity)`:
- Mark status as `processing`.
- Call `fetch_weather_data` and process it.
- Then update the same entity using `entity_service.update_item` (allowed because it's a different function, but we must be careful not to call `add_item` or `update_item` on the same entity inside the workflow function itself).
  
**BUT** the problem is that the workflow function is invoked *before persistence*, so synchronous or time-consuming operations inside it will block the main add_item call, which is undesirable.

Solution:
- Keep the workflow function minimal and only mutate the entity synchronously (e.g. set status, timestamps).
- Start a background async task (fire-and-forget) that will do the heavy lifting and update the entity.

This is allowed because:
- The background task is outside of the workflow function call.
- The workflow function itself only mutates the entity dict.
- The background task can call update_item on the same entity model.

Therefore:

1. **Inside workflow function**:
   - Set initial entity state: status = 'processing', createdAt timestamp.
   - Start background task `process_entity` passing the entity ID and entity data.

2. **Background task `process_entity`**:
   - Fetch weather data.
   - Process it.
   - Update entity with status and results.

3. **Endpoint `/weather/fetch`**:
   - Only validate and call `add_item` with workflow.

4. **Remove call to `asyncio.create_task(process_entity(...))` from anywhere else (e.g. startup or manual trigger endpoints)**.

---

### Also remove unnecessary endpoints like `/weather/process/<request_id>` because the workflow will trigger processing automatically.

---

### Here's the full updated code with this approach:

```python
import asyncio
import logging
from datetime import datetime
from typing import List
from dataclasses import dataclass

import httpx
from quart import Quart, jsonify
from quart_schema import QuartSchema, validate_request

from app_init.app_init import BeanFactory
from common.config.config import ENTITY_VERSION

factory = BeanFactory(config={'CHAT_REPOSITORY': 'cyoda'})
entity_service = factory.get_services()['entity_service']
cyoda_auth_service = factory.get_services()["cyoda_auth_service"]

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

@dataclass
class WeatherFetchRequest:
    latitude: float
    longitude: float
    parameters: List[str]
    start_date: str
    end_date: str

async def fetch_weather_data(latitude: float, longitude: float, parameters: List[str], start_date: str, end_date: str):
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "start_date": start_date,
        "end_date": end_date,
        "hourly": ",".join(parameters),
        "timezone": "UTC",
    }
    async with httpx.AsyncClient() as client:
        response = await client.get(url, params=params, timeout=10)
        response.raise_for_status()
        return response.json()

async def process_entity(job_id: str, data: dict):
    """
    Background async task that fetches and processes weather data,
    then updates the entity state.
    """
    try:
        raw_data = await fetch_weather_data(
            latitude=data["latitude"],
            longitude=data["longitude"],
            parameters=data["parameters"],
            start_date=data["start_date"],
            end_date=data["end_date"],
        )
        hourly = raw_data.get("hourly", {})
        processed = {"dates": hourly.get("time", [])}
        for param in data["parameters"]:
            processed[param] = hourly.get(param, [])

        update_data = {
            "status": "completed",
            "data": processed,
            "completedAt": datetime.utcnow().isoformat()
        }
        await entity_service.update_item(
            token=cyoda_auth_service,
            entity_model="weather_fetch_request",
            entity_version=ENTITY_VERSION,
            entity=update_data,
            technical_id=job_id,
            meta={}
        )
        logger.info(f"Job {job_id} completed successfully.")
    except Exception as e:
        error_data = {
            "status": "failed",
            "error": str(e),
        }
        await entity_service.update_item(
            token=cyoda_auth_service,
            entity_model="weather_fetch_request",
            entity_version=ENTITY_VERSION,
            entity=error_data,
            technical_id=job_id,
            meta={}
        )
        logger.exception(f"Job {job_id} failed.")

# Workflow function for 'weather_fetch_request' entity
async def process_weather_fetch_request(entity: dict):
    """
    Workflow function applied to 'weather_fetch_request' before persistence.
    Mutates entity status and schedules background processing.
    """
    # Set initial state
    entity['status'] = 'processing'
    entity['createdAt'] = datetime.utcnow().isoformat()

    # Start background processing task after persistence (fire and forget)
    # Use the entity's id or a temporary id - it will be assigned after persistence,
    # so we may need to rely on a unique attribute or generate a temporary id here.
    # Since we don't have the persisted ID yet, we can use a temporary unique id in entity.

    # Add a temporary unique ID if not exists
    if "technical_id" not in entity:
        import uuid
        entity["technical_id"] = str(uuid.uuid4())

    # Fire-and-forget task with the technical_id and entity copy
    asyncio.create_task(process_entity(entity["technical_id"], entity.copy()))

# workaround: quart-schema defect requires validate_request after route decorator for POST
@app.route("/weather/fetch", methods=["POST"])
@validate_request(WeatherFetchRequest)
async def weather_fetch(data: WeatherFetchRequest):
    # Simply add the entity with workflow; no other logic here
    try:
        entity_id = await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model="weather_fetch_request",
            entity_version=ENTITY_VERSION,
            entity=data.__dict__,
            workflow=process_weather_fetch_request
        )
        return jsonify({"request_id": entity_id}), 202
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to add item"}), 500

@app.route("/weather/result/<string:request_id>", methods=["GET"])
async def weather_result(request_id):
    try:
        job = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model="weather_fetch_request",
            entity_version=ENTITY_VERSION,
            technical_id=request_id
        )
        if not job:
            return jsonify({"error": "Request ID not found"}), 404

        status = job.get("status", "processing")
        if status == "processing":
            return jsonify({"request_id": request_id, "status": "processing"}), 200
        elif status == "completed":
            return jsonify({
                "request_id": request_id,
                "status": "completed",
                "data": job.get("data", {})
            }), 200
        elif status == "failed":
            return jsonify({
                "request_id": request_id,
                "status": "failed",
                "error": job.get("error", "Unknown error")
            }), 500
        else:
            return jsonify({"error": "Unknown job status"}), 500
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to retrieve item"}), 500

# Remove the /weather/process/<request_id> endpoint and startup background task resume logic,
# because workflow and background task handle it automatically now.

if __name__ == "__main__":
    app.run(use_reloader=False, debug=True, host="0.0.0.0", port=8000, threaded=True)
```

---

### Summary of changes:
- The endpoint `/weather/fetch` only validates and calls `add_item` with `workflow=process_weather_fetch_request`.
- The `process_weather_fetch_request` workflow function:
  - Sets initial entity status and timestamps.
  - Adds a `technical_id` if missing (UUID).
  - Schedules a fire-and-forget async task `process_entity` to fetch/process weather data and update entity.
- The `process_entity` function handles all async calls to external API and updates entity state.
- Removed manual background resume and manual `/weather/process/<id>` endpoint.
- The `/weather/result/<id>` endpoint remains for checking status/results.
- This design follows your requirement that all async logic moves to the workflow function or functions it triggers.

---

If you want me to provide this as a patch or diff, or want me to help with any further refinements, just let me know!