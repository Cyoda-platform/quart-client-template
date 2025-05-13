Understood! We'll move as much logic as possible from the endpoints into the workflow functions (`process_entity_job` here), so that the controller code is minimal and the business logic, including async tasks, is handled inside the workflow.

This means:

- The queueing logic and setting initial state can remain in the controller (since `add_item` requires an entity to be passed).
- The heavy lifting like fetching weather data, updating the entity status and results will be done inside the workflow function.
- Since the workflow function is called **before** persistence, to change the entity state we just modify the entity dict.
- For asynchronous work that requires external updates (such as updating the same entity after fetching results), we cannot call `update_item` on the same entity_model inside the workflow (would cause recursion).
- So, for async tasks that require updating the entity later, we have two options:
  1. Split the operation into multiple entities - e.g., create separate entities for jobs status and results, or
  2. Schedule fire-and-forget tasks external to the workflow (e.g., via message queue or separate worker).

But since the prompt says the workflow function **is a direct alternative for fire-and-forget async tasks**, and we cannot update the same entity_model inside the workflow function, the best approach here is to move all **initial state setting** and **fire-and-forget async task launching** into the workflow, but keep only the initial `add_item` call in the controller.

Therefore, the workflow function will:

- Set the entity state to "queued" or "processing"
- Launch the async fetch weather task (fire and forget)
- That async fetch weather task will update the entity later with the results via `update_item` (allowed because it's outside the workflow and updating the same entity_model is allowed there).

### Summary of changes:

- Controller just calls `add_item` with minimal data.
- The workflow function `process_entity_job`:
  - sets initial status `"queued"`
  - schedules the async fetch task (`asyncio.create_task(...)`).
- The fetch task runs outside the workflow and updates the entity when done.
- No direct update calls to the same entity_model inside the workflow.

---

## Updated Code

```python
from dataclasses import dataclass
import asyncio
import logging
from datetime import datetime
import uuid

from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request

import httpx
from app_init.app_init import BeanFactory

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

factory = BeanFactory(config={'CHAT_REPOSITORY': 'cyoda'})
entity_service = factory.get_services()['entity_service']
cyoda_auth_service = factory.get_services()["cyoda_auth_service"]

ENTITY_VERSION = None
from common.config.config import ENTITY_VERSION

@dataclass
class FetchWeatherRequest:
    location: str
    parameters: list
    date: str = None

async def fetch_weather_from_msgeomet(location: str, parameters: list, date: str = None):
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            url = f"https://api.meteo.lt/v1/places/{location}/forecasts/long-term"
            resp = await client.get(url)
            resp.raise_for_status()
            data = resp.json()
            forecasts = data.get("forecastTimestamps", [])
            if not forecasts:
                return {}
            forecast = forecasts[0]
            extracted = {}
            if "temperature" in parameters and "airTemperature" in forecast:
                extracted["temperature"] = forecast["airTemperature"]
            if "humidity" in parameters and "relativeHumidity" in forecast:
                extracted["humidity"] = forecast["relativeHumidity"]
            if "wind_speed" in parameters and "windSpeed" in forecast:
                extracted["wind_speed"] = forecast["windSpeed"]
            return extracted
        except Exception as e:
            logger.exception(f"Error fetching weather from MSC GeoMet: {e}")
            return None

async def process_entity_job(entity):
    """
    Workflow function applied to 'entity_job' entities asynchronously before persistence.
    
    This function sets initial state and schedules the async fetch task.
    """
    # Ensure requestedAt is set
    if "requestedAt" not in entity:
        entity["requestedAt"] = datetime.utcnow().isoformat() + "Z"
    
    # Set initial status
    entity["status"] = "queued"
    
    # Extract necessary info for async fetch task
    location = entity.get("location")
    parameters = entity.get("parameters")
    date = entity.get("date")
    technical_id = entity.get("technical_id")  # We need to set or pass this to identify entity later
    
    # If technical_id is not set, generate one and set it
    if not technical_id:
        technical_id = str(uuid.uuid4())
        entity["technical_id"] = technical_id
    
    # Launch the async processing task (fire and forget)
    asyncio.create_task(_async_process_entity_job(technical_id, location, parameters, date))
    
    # Return entity with updated status and technical_id
    return entity

async def _async_process_entity_job(job_id: str, location: str, parameters: list, date: str):
    """
    The actual async task that fetches weather data and updates the entity_job.
    Runs outside the workflow function.
    """
    try:
        # Update status to processing
        await entity_service.update_item(
            token=cyoda_auth_service,
            entity_model="entity_job",
            entity_version=ENTITY_VERSION,
            technical_id=job_id,
            entity={"status": "processing"},
            meta={}
        )
        data = await fetch_weather_from_msgeomet(location, parameters, date)
        if data is None:
            await entity_service.update_item(
                token=cyoda_auth_service,
                entity_model="entity_job",
                entity_version=ENTITY_VERSION,
                technical_id=job_id,
                entity={"status": "error", "result": {}},
                meta={}
            )
        else:
            result_data = {
                "status": "completed",
                "result": {
                    "location": location,
                    "parameters": data,
                    "date": date if date else datetime.utcnow().strftime("%Y-%m-%d"),
                    "retrieved_at": datetime.utcnow().isoformat() + "Z",
                }
            }
            await entity_service.update_item(
                token=cyoda_auth_service,
                entity_model="entity_job",
                entity_version=ENTITY_VERSION,
                technical_id=job_id,
                entity=result_data,
                meta={}
            )
    except Exception as e:
        logger.exception(e)
        await entity_service.update_item(
            token=cyoda_auth_service,
            entity_model="entity_job",
            entity_version=ENTITY_VERSION,
            technical_id=job_id,
            entity={"status": "error", "result": {}},
            meta={}
        )

@app.route("/weather/fetch", methods=["POST"])
@validate_request(FetchWeatherRequest)
async def fetch_weather(data: FetchWeatherRequest):
    # Compose the initial entity with request data
    entity = {
        "location": data.location,
        "parameters": data.parameters,
        "date": data.date,
        # Note: don't set status or requestedAt here, workflow will handle it
    }
    # Add the entity with workflow function; this will set status and launch async task automatically
    entity_id = await entity_service.add_item(
        token=cyoda_auth_service,
        entity_model="entity_job",
        entity_version=ENTITY_VERSION,
        entity=entity,
        workflow=process_entity_job
    )
    return jsonify({
        "status": "success",
        "fetch_id": entity_id,
        "message": "Data fetching started"
    })

@app.route("/weather/result/<string:fetch_id>", methods=["GET"])
async def get_result(fetch_id: str):
    job = await entity_service.get_item(
        token=cyoda_auth_service,
        entity_model="entity_job",
        entity_version=ENTITY_VERSION,
        technical_id=fetch_id
    )
    if not job:
        return jsonify({"status": "error", "message": "fetch_id not found"}), 404
    if job.get("status") in ("processing", "queued"):
        return jsonify({"status": "processing", "message": "Result not ready yet"}), 202
    if job.get("status") == "error":
        return jsonify({"status": "error", "message": "Failed to fetch data"}), 500
    return jsonify({
        "fetch_id": fetch_id,
        **job.get("result", {}),
    })

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
```

---

### Explanation:

- The controller `fetch_weather` now only prepares the entity data (location, parameters, date).
- It calls `add_item` with the `workflow=process_entity_job`.
- The workflow function:
  - Adds `requestedAt` timestamp,
  - Sets status `"queued"`,
  - Generates a `technical_id` if not set,
  - Launches the async task `_async_process_entity_job` via `asyncio.create_task()` that will fetch and update the entity asynchronously.
- The async task `_async_process_entity_job` runs outside the workflow and updates the entity status and result via `update_item`.
- This approach removes all heavy logic and fire-and-forget task launching from the controller.
- The workflow function modifies the entity in-place before persistence, as required.
- Controller remains clean, only handling validation and initial entity creation.

---

If you want, I can help you split the `technical_id` generation logic or add validation inside the workflow too. Let me know!