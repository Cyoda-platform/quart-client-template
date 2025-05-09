from dataclasses import dataclass, field, asdict
from typing import List, Optional

import asyncio
import logging
import uuid
from datetime import datetime

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request

from app_init.app_init import BeanFactory
from common.config.config import ENTITY_VERSION

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

factory = BeanFactory(config={'CHAT_REPOSITORY': 'cyoda'})
entity_service = factory.get_services()['entity_service']
cyoda_auth_service = factory.get_services()["cyoda_auth_service"]

# Constants
DEFAULT_PAGE_SIZE = 20

GOOGLE_PLACES_API_KEY = "YOUR_GOOGLE_PLACES_API_KEY"
GOOGLE_PLACES_SEARCH_URL = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"

@dataclass
class Location:
    latitude: float
    longitude: float

@dataclass
class Pagination:
    page: Optional[int] = 1
    page_size: Optional[int] = DEFAULT_PAGE_SIZE

@dataclass
class Filters:
    price_range: Optional[List[int]] = field(default_factory=list)  # e.g. [1,3]
    rating_min: Optional[float] = None
    cuisine_subtypes: Optional[List[str]] = field(default_factory=list)

@dataclass
class SearchRequest:
    location: Location
    radius: int
    filters: Optional[Filters] = field(default_factory=Filters)
    pagination: Optional[Pagination] = field(default_factory=Pagination)


@app.route("/api/search-restaurants", methods=["POST"])
@validate_request(SearchRequest)
async def search_restaurants(data: SearchRequest):
    search_id = str(uuid.uuid4())
    requested_at = datetime.utcnow().isoformat()

    initial_entity = {
        "search_id": search_id,
        "status": "processing",
        "requestedAt": requested_at,
        "request_data": asdict(data),
    }
    try:
        id_returned = await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model="search_result",
            entity_version=ENTITY_VERSION,
            entity=initial_entity,
            )
    except Exception as e:
        logger.exception(f"Failed to add search_result entity: {e}")
        return jsonify({"error": "Failed to initiate search"}), 500

    return jsonify({
        "search_id": search_id,
        "status": "processing",
        "requestedAt": requested_at,
        "message": "Search started, please poll results using GET /api/search-results/{search_id}"
    })


@app.route("/api/search-results/<search_id>", methods=["GET"])
async def get_search_results(search_id):
    page = request.args.get("page", default=None, type=int)
    page_size = request.args.get("page_size", default=None, type=int)

    try:
        entity_data = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model="search_result",
            entity_version=ENTITY_VERSION,
            technical_id=search_id
        )
    except Exception as e:
        logger.exception(f"Failed to retrieve search result from entity_service: {e}")
        return jsonify({"error": "Failed to retrieve search results"}), 500

    if not entity_data:
        return jsonify({"error": "search_id not found"}), 404

    status = entity_data.get("status", "processing")

    if status == "processing":
        return jsonify({
            "search_id": search_id,
            "status": "processing",
            "requestedAt": entity_data.get("requestedAt"),
            "message": "Search is still processing, please try again later."
        })

    if status == "error":
        return jsonify({
            "search_id": search_id,
            "status": "error",
            "error": entity_data.get("error")
        }), 500

    all_restaurants = entity_data.get("all_restaurants", [])
    total_results = entity_data.get("total_results", 0)

    # If client requested page/page_size different from stored, paginate again here
    current_page = page if page and page > 0 else entity_data.get("current_page", 1)
    current_page_size = page_size if page_size and page_size > 0 else entity_data.get("page_size", DEFAULT_PAGE_SIZE)

    restaurants_page = paginate(all_restaurants, current_page, current_page_size)

    response = {
        "search_id": search_id,
        "total_results": total_results,
        "page": current_page,
        "page_size": current_page_size,
        "restaurants": restaurants_page,
    }
    return jsonify(response)


if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)