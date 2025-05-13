Understood! The goal is to **move all async logic from the endpoints into workflow functions** (`process_{entity_name}`) that will be invoked right before the entity persistence. This way, controllers remain thin and simple, and all data manipulation, fetching, and secondary entity creation happens in the workflow.

### Key points and constraints:
- The workflow function takes the entity data as the only argument.
- It can modify the entity state directly (changing fields, adding fields).
- It can perform async logic (network calls, additional entity calls).
- It can create/update other entities of **different** entity models (but not the current entity model!).
- The workflow function is awaited inside `entity_service.add_item` before persisting the entity.
- The endpoint only creates the initial entity data and calls `add_item` with the workflow function.

---

### What async logic do we have that should be moved?

1. Fetching weather data from external API.
2. Updating/adding cache entities.
3. Managing job state.

---

### Approach:

- Define **one or more workflow functions** for the entity models involved:
  - `process_weather_cache` - which, given an entity with lat/lon, fetches weather data and modifies the entity accordingly.
  - `process_weather_fetch_job` (new) - which will fetch weather data for multiple locations and manage job state.
  
- In the `/weather/fetch` endpoint:
  - Instead of launching an async task to process all locations, we create a new job entity with initial data (e.g. job id, locations, status).
  - We call `entity_service.add_item` with the `process_weather_fetch_job` workflow.
  - The workflow will asynchronously fetch weather for each location, add/update weather_cache entities (of different entity_model), and update the job status.
  
- In the `/weather/results` endpoint:
  - It remains a simple GET fetching the cached weather entity by technical_id.
  
---

### Additional notes:

- Since we **cannot add/update/delete the same entity model inside its own workflow** (to avoid recursion), for the job entity, the workflow can update other entities (e.g. `weather_cache`), and for the weather cache entity, the workflow can only update the entity itself.
- For the weather fetch job, the workflow can update the job entity state directly (status, timestamps).
- For weather cache, the workflow fetches data and updates the entity data before persistence.

---

### Proposed new structure:

- `process_weather_fetch_job(entity)`:
  - entity contains e.g. `job_id`, `locations`, `status`
  - For each location:
    - Call `entity_service.add_item` with entity_model=`weather_cache`, data containing lat/lon (or minimal info), workflow=`process_weather_cache`
  - Update job status on `entity` directly.
- `process_weather_cache(entity)`:
  - Given lat/lon in entity, fetch weather data from external API.
  - Update entity with new data fields (weather data, timestamp, processed_at, etc).
  
---

### Now, full updated code reflecting these changes:

```python
import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Dict

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request, validate_querystring

from app_init.app_init import BeanFactory
from common.config.config import ENTITY_VERSION

factory = BeanFactory(config={'CHAT_REPOSITORY': 'cyoda'})
entity_service = factory.get_services()['entity_service']
cyoda_auth_service = factory.get_services()["cyoda_auth_service"]

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# Request schemas
@dataclass
class FetchRequest:
    locations: list  # List of {"latitude": float, "longitude": float}

@dataclass
class WeatherQuery:
    lat: float
    lon: float

entity_name_cache = "weather_cache"  # entity name always underscore lowercase
entity_name_job = "weather_fetch_job"  # new entity for fetch job

MSC_GEOMET_BASE_URL = "https://api.msc-geomet.com/weather"  # TODO: replace with actual URL


async def fetch_weather_data(lat: float, lon: float) -> Dict:
    """
    Helper to fetch weather data from external API.
    """
    async with httpx.AsyncClient() as client:
        params = {"lat": lat, "lon": lon}
        response = await client.get(MSC_GEOMET_BASE_URL, params=params, timeout=10)
        response.raise_for_status()
        return response.json()


async def process_weather_cache(entity: dict) -> dict:
    """
    Workflow function for 'weather_cache' entity.
    Fetches weather data for the lat/lon and updates the entity before persistence.
    """
    lat = entity.get("latitude")
    lon = entity.get("longitude")
    if lat is None or lon is None:
        logger.warning("process_weather_cache: latitude or longitude missing in entity")
        return entity  # no modification

    try:
        data = await fetch_weather_data(lat, lon)
        entity["data"] = data
        entity["timestamp"] = datetime.utcnow().isoformat() + "Z"
        entity["processed_at"] = datetime.utcnow().isoformat() + "Z"
        logger.info(f"Weather data fetched and updated for ({lat}, {lon})")
    except Exception as e:
        logger.exception(f"Failed to fetch weather data in process_weather_cache: {e}")
        # optionally add error info to entity
        entity["fetch_error"] = str(e)
    return entity


async def process_weather_fetch_job(entity: dict) -> dict:
    """
    Workflow function for 'weather_fetch_job' entity.
    Process the fetch job by adding/updating weather_cache entities with workflow.
    Updates the job status in this entity.
    """
    job_id = entity.get("job_id")
    locations = entity.get("locations", [])
    if not job_id or not isinstance(locations, list) or not locations:
        entity["status"] = "failed"
        entity["error"] = "Invalid job_id or locations data"
        logger.error(f"process_weather_fetch_job: invalid input for job: {entity}")
        return entity

    entity["status"] = "processing"
    entity["started_at"] = datetime.utcnow().isoformat() + "Z"

    logger.info(f"Starting job {job_id} for {len(locations)} locations")

    # For each location, add or update weather_cache entity with workflow
    for loc in locations:
        lat = loc.get("latitude")
        lon = loc.get("longitude")
        if lat is None or lon is None:
            logger.warning(f"Skipping location with missing coordinates: {loc}")
            continue

        technical_id = f"{lat}_{lon}"

        # Prepare cache entity minimal data
        cache_entity = {
            "latitude": lat,
            "longitude": lon,
            # 'data', 'timestamp' etc will be filled by workflow
        }

        try:
            # Try to update first (if exists)
            await entity_service.update_item(
                token=cyoda_auth_service,
                entity_model=entity_name_cache,
                entity_version=ENTITY_VERSION,
                entity=cache_entity,
                technical_id=technical_id,
                meta={},
            )
            logger.info(f"Updated existing cache entity for ({lat},{lon})")
        except Exception:
            # If update fails, add new item with workflow function
            await entity_service.add_item(
                token=cyoda_auth_service,
                entity_model=entity_name_cache,
                entity_version=ENTITY_VERSION,
                entity=cache_entity,
                workflow=process_weather_cache,
            )
            logger.info(f"Added new cache entity for ({lat},{lon}) with workflow")

        # Note: The workflow `process_weather_cache` will fetch and update weather data asynchronously
        # before persistence.

    entity["status"] = "done"
    entity["finished_at"] = datetime.utcnow().isoformat() + "Z"
    logger.info(f"Job {job_id} processing complete")

    return entity


@app.route("/weather/fetch", methods=["POST"])
@validate_request(FetchRequest)
async def weather_fetch(data: FetchRequest):
    locations = data.locations
    if not isinstance(locations, list) or not locations:
        return jsonify({"status": "error", "message": "No locations provided"}), 400

    job_id = f"job_{datetime.utcnow().timestamp()}"
    job_entity = {
        "job_id": job_id,
        "locations": locations,
        "status": "new",
        "requested_at": datetime.utcnow().isoformat() + "Z",
    }

    # Add the job entity with the workflow to process it asynchronously before persistence
    await entity_service.add_item(
        token=cyoda_auth_service,
        entity_model=entity_name_job,
        entity_version=ENTITY_VERSION,
        entity=job_entity,
        workflow=process_weather_fetch_job,
    )

    # The processing is handled in the workflow function; no fire-and-forget needed here
    return jsonify(
        {
            "status": "success",
            "message": "Weather data fetching job created",
            "job_id": job_id,
            "requested_locations": len(locations),
        }
    )


@validate_querystring(WeatherQuery)
@app.route("/weather/results", methods=["GET"])
async def weather_results():
    lat = request.args.get("lat", type=float)
    lon = request.args.get("lon", type=float)
    if lat is None or lon is None:
        return jsonify({"status": "error", "message": "lat and lon query parameters required"}), 400

    technical_id = f"{lat}_{lon}"
    try:
        cached = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model=entity_name_cache,
            entity_version=ENTITY_VERSION,
            technical_id=technical_id,
        )
    except Exception as e:
        logger.exception(f"Failed to get cached weather data for ({lat}, {lon}): {e}")
        cached = None

    if not cached:
        return (
            jsonify(
                {"status": "error", "message": "No weather data found for the requested location"}
            ),
            404,
        )

    return jsonify(
        {
            "location": {"latitude": lat, "longitude": lon},
            "weather": cached.get("data"),
            "timestamp": cached.get("timestamp"),
        }
    )


if __name__ == "__main__":
    app.run(use_reloader=False, debug=True, host="0.0.0.0", port=8000, threaded=True)
```

---

### Explanation of changes:

- Introduced a new entity model `weather_fetch_job` to represent each fetch request.
- Endpoint `/weather/fetch` only creates the job entity and calls `add_item` with `process_weather_fetch_job` workflow.
- `process_weather_fetch_job` asynchronously processes all locations by calling `entity_service.add_item` for `weather_cache` entities with `process_weather_cache` workflow.
- `process_weather_cache` fetches the weather data from external API and updates the entity before persistence.
- Removed all async fetching logic from endpoints.
- No fire-and-forget tasks in endpoints, the workflow functions handle asynchronous fetching and persistence.
- Job entity status is updated inside its workflow function (`new` → `processing` → `done` or `failed`).
- Weather cache entities are created/updated by the job workflow, each enriched by their own workflow function.

---

### Benefits:
- Controllers are thin, only responsible for input validation and calling `add_item` with the proper workflow.
- All business logic, async calls, entity manipulation, and state management are inside workflow functions.
- Robust, maintainable, and easily testable.
- Respects the constraint of no recursion on current entity model inside its own workflow.

---

If you want, I can help refactor further or adjust error handling/logging. Let me know!