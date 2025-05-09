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

# In-memory cache to mock persistence: search_id -> search results & metadata
search_cache = {}

# Google Places API details (replace with your actual API key)
GOOGLE_PLACES_API_KEY = "YOUR_GOOGLE_PLACES_API_KEY"
GOOGLE_PLACES_SEARCH_URL = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"

# Constants
DEFAULT_PAGE_SIZE = 20


async def fetch_restaurants_from_google(location, radius, filters):
    """
    Query Google Places Nearby Search API for French restaurants within radius.
    Apply filters client-side as Google API does not support all filters directly.
    """

    params = {
        "key": GOOGLE_PLACES_API_KEY,
        "location": f"{location['latitude']},{location['longitude']}",
        "radius": radius,
        "keyword": "french restaurant",
        "type": "restaurant",
    }

    restaurants = []
    async with httpx.AsyncClient() as client:
        next_page_token = None
        while True:
            if next_page_token:
                # Google requires short delay before using next_page_token
                await asyncio.sleep(2)
                params["pagetoken"] = next_page_token

            try:
                resp = await client.get(GOOGLE_PLACES_SEARCH_URL, params=params, timeout=10)
                resp.raise_for_status()
                data = resp.json()
            except Exception as e:
                logger.exception(f"Google Places API request failed: {e}")
                break

            results = data.get("results", [])
            restaurants.extend(results)

            next_page_token = data.get("next_page_token")
            if not next_page_token:
                break

            # Limit results for prototype to max ~60 (3 pages)
            if len(restaurants) >= 60:
                break

    # Apply additional filters not supported by Google API
    filtered = []
    price_range = filters.get("price_range")
    rating_min = filters.get("rating_min")
    cuisine_subtypes = filters.get("cuisine_subtypes", [])

    for r in restaurants:
        # Price level: Google gives 0-4, treat 0 as unknown
        price_level = r.get("price_level", 0)
        rating = r.get("rating", 0)

        # Filtering price_range if specified
        if price_range:
            if price_level == 0 or not (price_range[0] <= price_level <= price_range[1]):
                continue

        # Filtering rating minimum
        if rating_min and rating < rating_min:
            continue

        # Filtering cuisine subtypes (mocked, as Google API may not provide detailed cuisine)
        # TODO: Improve cuisine subtype filtering with additional data source if possible
        if cuisine_subtypes:
            # We check if any subtype keyword appears in name or vicinity as a basic heuristic
            name = r.get("name", "").lower()
            vicinity = r.get("vicinity", "").lower()
            if not any(subtype.lower() in name or subtype.lower() in vicinity for subtype in cuisine_subtypes):
                continue

        filtered.append(r)

    return filtered


def paginate(items, page, page_size):
    start = (page - 1) * page_size
    end = start + page_size
    return items[start:end]


def format_restaurant(raw):
    """
    Normalize Google Places restaurant data to our API response format.
    """
    return {
        "id": raw.get("place_id"),
        "name": raw.get("name"),
        "address": raw.get("vicinity"),
        "contact": raw.get("formatted_phone_number", ""),  # Not provided by Places Nearby Search API
        "rating": raw.get("rating"),
        "price_level": raw.get("price_level", 0),
        "cuisine_types": ["French"],  # Base assumption from search keyword
        "location": {
            "latitude": raw.get("geometry", {}).get("location", {}).get("lat"),
            "longitude": raw.get("geometry", {}).get("location", {}).get("lng"),
        },
    }


async def process_search_job(search_id, request_data):
    """
    Background task to fetch and process restaurants, store results in cache.
    """
    try:
        logger.info(f"Processing search job {search_id} started")
        location = request_data["location"]
        radius = request_data["radius"]
        filters = request_data.get("filters", {})
        pagination = request_data.get("pagination", {"page": 1, "page_size": DEFAULT_PAGE_SIZE})

        raw_restaurants = await fetch_restaurants_from_google(location, radius, filters)
        total_results = len(raw_restaurants)

        # Format all results
        all_restaurants = [format_restaurant(r) for r in raw_restaurants]

        # Store full results and metadata in cache
        search_cache[search_id]["status"] = "completed"
        search_cache[search_id]["completedAt"] = datetime.utcnow().isoformat()
        search_cache[search_id]["total_results"] = total_results
        search_cache[search_id]["all_restaurants"] = all_restaurants

        # Prepare first page response data
        page = pagination.get("page", 1)
        page_size = pagination.get("page_size", DEFAULT_PAGE_SIZE)
        restaurants_page = paginate(all_restaurants, page, page_size)
        search_cache[search_id]["current_page"] = page
        search_cache[search_id]["page_size"] = page_size
        search_cache[search_id]["restaurants_page"] = restaurants_page

        logger.info(f"Processing search job {search_id} completed with {total_results} results")
    except Exception as e:
        logger.exception(f"Error processing search job {search_id}: {e}")
        search_cache[search_id]["status"] = "error"
        search_cache[search_id]["error"] = str(e)


@app.route("/api/search-restaurants", methods=["POST"])
async def search_restaurants():
    data = await request.get_json(force=True)
    # Basic validation, more can be added later
    if not data or "location" not in data or "radius" not in data:
        return jsonify({"error": "Missing required fields: location and radius"}), 400

    search_id = str(uuid.uuid4())
    requested_at = datetime.utcnow().isoformat()
    search_cache[search_id] = {
        "status": "processing",
        "requestedAt": requested_at,
        "request_data": data,
    }

    # Fire and forget processing task
    asyncio.create_task(process_search_job(search_id, data))

    # Initial response: status processing, no results yet
    return jsonify({
        "search_id": search_id,
        "status": "processing",
        "requestedAt": requested_at,
        "message": "Search started, please poll results using GET /api/search-results/{search_id}"
    })


@app.route("/api/search-results/<search_id>", methods=["GET"])
async def get_search_results(search_id):
    page = request.args.get("page", default=1, type=int)
    page_size = request.args.get("page_size", default=DEFAULT_PAGE_SIZE, type=int)

    cached = search_cache.get(search_id)
    if not cached:
        return jsonify({"error": "search_id not found"}), 404

    status = cached.get("status", "processing")
    if status == "processing":
        return jsonify({
            "search_id": search_id,
            "status": "processing",
            "requestedAt": cached.get("requestedAt"),
            "message": "Search is still processing, please try again later."
        })

    if status == "error":
        return jsonify({
            "search_id": search_id,
            "status": "error",
            "error": cached.get("error")
        }), 500

    # If completed, return paginated results
    all_restaurants = cached.get("all_restaurants", [])
    total_results = cached.get("total_results", 0)

    restaurants_page = paginate(all_restaurants, page, page_size)

    response = {
        "search_id": search_id,
        "total_results": total_results,
        "page": page,
        "page_size": page_size,
        "restaurants": restaurants_page,
    }
    return jsonify(response)


if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
```
