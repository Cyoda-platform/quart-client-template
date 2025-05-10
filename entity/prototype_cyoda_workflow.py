from dataclasses import dataclass
from quart import Quart, jsonify
from quart_schema import QuartSchema, validate_request
import logging
import uuid
from datetime import datetime
import httpx

from app_init.app_init import BeanFactory
from common.config.config import ENTITY_VERSION

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

factory = BeanFactory(config={'CHAT_REPOSITORY': 'cyoda'})
entity_service = factory.get_services()['entity_service']
cyoda_auth_service = factory.get_services()["cyoda_auth_service"]

app = Quart(__name__)
QuartSchema(app)

@dataclass
class RandomCatRequest:
    includeBreedInfo: bool = True
    catId: str = None  # will be set by endpoint, carried through entity

async def fetch_random_cat(include_breed_info: bool):
    # External async call to fetch random cat data from API.
    url = "https://api.thecatapi.com/v1/images/search"
    params = {"include_breeds": "1" if include_breed_info else "0"}

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()
            if not data or len(data) == 0:
                raise ValueError("No cat data returned from external API")
            return data[0]
    except Exception as e:
        logger.exception("Error fetching cat data from external API")
        raise

async def process_random_cat_request(entity):
    # Workflow function applied to 'random_cat_request' entities before persistence.
    try:
        # Fetch cat data asynchronously
        cat_raw = await fetch_random_cat(entity.get("includeBreedInfo", True))

        # Extract breed info if requested and available
        breed_info = None
        if entity.get("includeBreedInfo", True) and cat_raw.get("breeds"):
            breed = cat_raw["breeds"][0]
            breed_info = {
                "name": breed.get("name"),
                "origin": breed.get("origin"),
                "temperament": breed.get("temperament"),
                "description": breed.get("description"),
            }

        # Update the entity with fetched data
        entity["imageUrl"] = cat_raw.get("url")
        entity["breed"] = breed_info
        entity["fetchedAt"] = datetime.utcnow().isoformat() + "Z"
        entity["status"] = "completed"
        entity["completedAt"] = datetime.utcnow().isoformat() + "Z"

        logger.info(f"Workflow processed random_cat_request entity catId={entity.get('catId')} successfully.")

    except Exception as e:
        # On error, update entity status and add error message
        entity["status"] = "failed"
        entity["error"] = str(e)
        entity["completedAt"] = datetime.utcnow().isoformat() + "Z"
        logger.exception(f"Workflow failed processing random_cat_request entity catId={entity.get('catId')}.")

@app.route("/cats/random", methods=["POST"])
@validate_request(RandomCatRequest)
async def post_random_cat(data: RandomCatRequest):
    # Generate unique catId
    cat_id = str(uuid.uuid4())

    # Prepare initial entity state with minimal data.
    # status is "processing" initially and timestamps are set.
    entity = {
        "catId": cat_id,
        "includeBreedInfo": data.includeBreedInfo,
        "status": "processing",
        "requestedAt": datetime.utcnow().isoformat() + "Z",
    }

    # Add entity with workflow function that performs async processing before persistence.
    try:
        await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model="random_cat_request",
            entity_version=ENTITY_VERSION,
            entity=entity,
            workflow=process_random_cat_request
        )
    except Exception as e:
        logger.exception("Failed to add entity with workflow")
        return jsonify({
            "error": "Failed to initiate random cat request",
            "details": str(e)
        }), 500

    # Immediately return with 202 Accepted with catId and status
    return jsonify({
        "catId": cat_id,
        "status": "processing",
        "message": "Cat data is being fetched. Use GET /cats/random/{catId} to retrieve results."
    }), 202

@app.route("/cats/random/<cat_id>", methods=["GET"])
async def get_random_cat(cat_id):
    try:
        stored = await entity_service.get_items_by_condition(
            token=cyoda_auth_service,
            entity_model="random_cat_request",
            entity_version=ENTITY_VERSION,
            condition={"catId": cat_id}
        )
        if stored and len(stored) > 0:
            return jsonify(stored[0])
        else:
            return jsonify({
                "error": "Cat data not found or still processing",
                "catId": cat_id
            }), 404
    except Exception as e:
        logger.exception(f"Failed to retrieve cat data for catId={cat_id}")
        return jsonify({
            "error": "Internal server error",
            "details": str(e)
        }), 500

if __name__ == '__main__':
    import sys
    import logging

    logging.basicConfig(stream=sys.stdout, level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s - %(message)s")

    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)