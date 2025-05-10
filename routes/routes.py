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