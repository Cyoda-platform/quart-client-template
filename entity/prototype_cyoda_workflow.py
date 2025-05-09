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


async def fetch_restaurants_from_google(location, radius, filters):
    params = {
        "key": GOOGLE_PLACES_API_KEY,
        "location": f"{location.latitude},{location.longitude}",
        "radius": radius,
        "keyword": "french restaurant",
        "type": "restaurant",
    }

    restaurants = []
    async with httpx.AsyncClient() as client:
        next_page_token = None
        retry_attempts = 0
        while True:
            if next_page_token:
                # Google requires a short delay before using next_page_token
                await asyncio.sleep(2)
                params["pagetoken"] = next_page_token
            else:
                params.pop("pagetoken", None)
            try:
                resp = await client.get(GOOGLE_PLACES_SEARCH_URL, params=params, timeout=10)
                resp.raise_for_status()
                data = resp.json()
            except Exception as e:
                logger.exception(f"Google Places API request failed: {e}")
                # Retry logic for transient errors up to 2 times
                retry_attempts += 1
                if retry_attempts > 2:
                    break
                await asyncio.sleep(2)
                continue

            retry_attempts = 0
            results = data.get("results", [])
            restaurants.extend(results)

            next_page_token = data.get("next_page_token")
            if not next_page_token:
                break

            if len(restaurants) >= 60:
                break

    filtered = []
    price_range = filters.price_range if filters else None
    rating_min = filters.rating_min if filters else None
    cuisine_subtypes = filters.cuisine_subtypes if filters else []

    for r in restaurants:
        price_level = r.get("price_level", 0)
        rating = r.get("rating", 0)

        if price_range:
            if price_level == 0 or not (price_range[0] <= price_level <= price_range[1]):
                continue

        if rating_min and rating < rating_min:
            continue

        if cuisine_subtypes:
            name = r.get("name", "").lower()
            vicinity = r.get("vicinity", "").lower()
            if not any(subtype.lower() in name or subtype.lower() in vicinity for subtype in cuisine_subtypes):
                continue

        filtered.append(r)

    return filtered


def paginate(items, page, page_size):
    if page < 1:
        page = 1
    if page_size < 1:
        page_size = DEFAULT_PAGE_SIZE
    start = (page - 1) * page_size
    end = start + page_size
    return items[start:end]


def format_restaurant(raw):
    return {
        "id": raw.get("place_id"),
        "name": raw.get("name"),
        "address": raw.get("vicinity"),
        "contact": "",  # Google Nearby Search does not provide contact info
        "rating": raw.get("rating"),
        "price_level": raw.get("price_level", 0),
        "cuisine_types": ["French"],
        "location": {
            "latitude": raw.get("geometry", {}).get("location", {}).get("lat"),
            "longitude": raw.get("geometry", {}).get("location", {}).get("lng"),
        },
    }


async def process_search_result(entity):
    """
    Workflow function applied to 'search_result' entity before persisting.
    Performs full search processing, data enrichment, and state updates.
    """
    try:
        logger.info(f"Workflow process_search_result started for search_id={entity.get('search_id')}")

        request_data = entity.get("request_data")
        if not request_data:
            entity["status"] = "error"
            entity["error"] = "Missing request_data"
            return entity

        loc = request_data.get("location")
        if not loc or "latitude" not in loc or "longitude" not in loc:
            entity["status"] = "error"
            entity["error"] = "Invalid location data"
            return entity
        location = Location(latitude=loc["latitude"], longitude=loc["longitude"])

        radius = request_data.get("radius")
        if radius is None or not isinstance(radius, int) or radius <= 0:
            entity["status"] = "error"
            entity["error"] = "Invalid radius"
            return entity

        filters_dict = request_data.get("filters", {})
        filters = Filters(
            price_range=filters_dict.get("price_range", []),
            rating_min=filters_dict.get("rating_min"),
            cuisine_subtypes=filters_dict.get("cuisine_subtypes", []),
        )
        pagination_dict = request_data.get("pagination", {})
        pagination = Pagination(
            page=pagination_dict.get("page", 1),
            page_size=pagination_dict.get("page_size", DEFAULT_PAGE_SIZE),
        )
        # Defensive: normalize pagination values
        if pagination.page is None or pagination.page < 1:
            pagination.page = 1
        if pagination.page_size is None or pagination.page_size < 1:
            pagination.page_size = DEFAULT_PAGE_SIZE

        # Fetch restaurants asynchronously
        raw_restaurants = await fetch_restaurants_from_google(
            location, radius, filters
        )
        total_results = len(raw_restaurants)
        all_restaurants = [format_restaurant(r) for r in raw_restaurants]

        # Paginate for requested page
        restaurants_page = paginate(all_restaurants, pagination.page, pagination.page_size)

        # Update entity state before persistence
        entity["status"] = "completed"
        entity["completedAt"] = datetime.utcnow().isoformat()
        entity["total_results"] = total_results
        entity["all_restaurants"] = all_restaurants
        entity["current_page"] = pagination.page
        entity["page_size"] = pagination.page_size
        entity["restaurants_page"] = restaurants_page
        entity["processedAt"] = datetime.utcnow().isoformat()

        logger.info(f"Workflow process_search_result completed for search_id={entity.get('search_id')} with {total_results} results")

    except Exception as e:
        logger.exception(f"Workflow process_search_result error: {e}")
        entity["status"] = "error"
        entity["error"] = str(e)

    return entity


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
            workflow=process_search_result
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