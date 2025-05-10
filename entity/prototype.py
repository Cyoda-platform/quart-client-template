```python
import asyncio
import logging
import uuid
from datetime import datetime

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# In-memory "cache" for fetched cat data
cat_data_cache = {}

# External APIs used:
# - TheCatAPI for random cat images and breed info: https://thecatapi.com/
#   (Free public API: https://api.thecatapi.com/v1/images/search?include_breeds=1)
# Note: No API key used here; for production, consider using a key.

async def fetch_random_cat(include_breed_info: bool):
    url = "https://api.thecatapi.com/v1/images/search"
    params = {"include_breeds": "1" if include_breed_info else "0"}

    async with httpx.AsyncClient(timeout=10) as client:
        try:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()
            if not data or len(data) == 0:
                raise ValueError("No cat data returned from external API")
            return data[0]
        except Exception as e:
            logger.exception("Failed to fetch cat data from external API")
            raise e

async def process_entity(entity_job, data):
    try:
        # Fetch cat data from external API
        cat_raw = await fetch_random_cat(data.get("includeBreedInfo", True))

        # Extract breed info if present
        breed_info = None
        if data.get("includeBreedInfo", True) and cat_raw.get("breeds"):
            breed = cat_raw["breeds"][0]
            breed_info = {
                "name": breed.get("name"),
                "origin": breed.get("origin"),
                "temperament": breed.get("temperament"),
                "description": breed.get("description"),
            }

        # Construct stored entity
        stored_entity = {
            "catId": data["catId"],
            "imageUrl": cat_raw.get("url"),
            "breed": breed_info,
            "fetchedAt": datetime.utcnow().isoformat() + "Z",
        }

        # Update cache
        entity_job[data["catId"]].update({
            "status": "completed",
            "result": stored_entity,
            "completedAt": datetime.utcnow().isoformat() + "Z",
        })

        cat_data_cache[data["catId"]] = stored_entity

        logger.info(f"Processed cat data for catId={data['catId']}")

    except Exception as e:
        entity_job[data["catId"]].update({
            "status": "failed",
            "error": str(e),
            "completedAt": datetime.utcnow().isoformat() + "Z",
        })
        logger.exception(f"Error processing cat data for catId={data['catId']}")

@app.route("/cats/random", methods=["POST"])
async def post_random_cat():
    try:
        data = await request.get_json(force=True)
    except Exception:
        data = {}

    include_breed_info = data.get("includeBreedInfo", True)
    cat_id = str(uuid.uuid4())

    # Initialize the job status
    entity_job = {}
    entity_job[cat_id] = {
        "status": "processing",
        "requestedAt": datetime.utcnow().isoformat() + "Z",
    }

    # Fire and forget the processing task
    await asyncio.create_task(process_entity(entity_job, {"catId": cat_id, "includeBreedInfo": include_breed_info}))

    # Immediately respond with the catId and status
    return jsonify({
        "catId": cat_id,
        "status": entity_job[cat_id]["status"],
        "message": "Cat data is being fetched. Use GET /cats/random/{catId} to retrieve results."
    }), 202

@app.route("/cats/random/<cat_id>", methods=["GET"])
async def get_random_cat(cat_id):
    stored = cat_data_cache.get(cat_id)
    if stored:
        return jsonify(stored)
    else:
        return jsonify({
            "error": "Cat data not found or still processing",
            "catId": cat_id
        }), 404

if __name__ == '__main__':
    import sys
    import logging

    # Set up basic console logging
    logging.basicConfig(stream=sys.stdout, level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s - %(message)s")

    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
```
