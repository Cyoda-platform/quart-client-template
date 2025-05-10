from dataclasses import dataclass
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request
import asyncio
import logging
import uuid
from datetime import datetime
import httpx

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

@dataclass
class RandomCatRequest:
    includeBreedInfo: bool = True

# In-memory "cache" for fetched cat data
cat_data_cache = {}

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
        cat_raw = await fetch_random_cat(data.includeBreedInfo)

        breed_info = None
        if data.includeBreedInfo and cat_raw.get("breeds"):
            breed = cat_raw["breeds"][0]
            breed_info = {
                "name": breed.get("name"),
                "origin": breed.get("origin"),
                "temperament": breed.get("temperament"),
                "description": breed.get("description"),
            }

        stored_entity = {
            "catId": data.catId,
            "imageUrl": cat_raw.get("url"),
            "breed": breed_info,
            "fetchedAt": datetime.utcnow().isoformat() + "Z",
        }

        entity_job[data.catId].update({
            "status": "completed",
            "result": stored_entity,
            "completedAt": datetime.utcnow().isoformat() + "Z",
        })

        cat_data_cache[data.catId] = stored_entity

        logger.info(f"Processed cat data for catId={data.catId}")

    except Exception as e:
        entity_job[data.catId].update({
            "status": "failed",
            "error": str(e),
            "completedAt": datetime.utcnow().isoformat() + "Z",
        })
        logger.exception(f"Error processing cat data for catId={data.catId}")

# POST route: validation last due to quart-schema issue workaround
@app.route("/cats/random", methods=["POST"])
@validate_request(RandomCatRequest)  # must be second decorator on POST
async def post_random_cat(data: RandomCatRequest):
    cat_id = str(uuid.uuid4())

    entity_job = {}
    entity_job[cat_id] = {
        "status": "processing",
        "requestedAt": datetime.utcnow().isoformat() + "Z",
    }

    # Fire and forget processing task
    await asyncio.create_task(process_entity(entity_job, RandomCatRequest(catId=cat_id, includeBreedInfo=data.includeBreedInfo)))

    return jsonify({
        "catId": cat_id,
        "status": entity_job[cat_id]["status"],
        "message": "Cat data is being fetched. Use GET /cats/random/{catId} to retrieve results."
    }), 202

# GET route: validation first due to quart-schema issue workaround
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

    logging.basicConfig(stream=sys.stdout, level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s - %(message)s")

    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
