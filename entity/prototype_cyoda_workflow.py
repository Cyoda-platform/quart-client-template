Absolutely, moving async business logic and side effects into the workflow function (`process_{entity_name}`) is a clean and robust approach, as it encapsulates the processing related to the entity and keeps the controller (endpoint) lean and focused on request/response handling.

---

### What to move:

- The entire async search job logic (`process_search_job`) that fetches, filters, paginates, formats, and updates the entity state.
- The creation/update of entity data related to the search results.
- Any state modifications or metadata additions related to the entity.
- The "fire and forget" async task currently launched by the endpoint with `asyncio.create_task`.

---

### What to keep in the endpoint:

- Validate and parse the incoming request.
- Create the initial entity with minimal data (e.g. `search_id`, `status` = processing).
- Call `entity_service.add_item` passing `workflow=process_search_result` so that all async logic happens inside the workflow function.
- Return the `search_id` and status to the client immediately.

---

### Important:

- Since you **cannot modify or add entities of the same model** inside the workflow (to avoid infinite recursion), the workflow function must **only modify the entity data passed in**. It can **fetch** other entities or **add** entities of other models (if needed).
- We will do all processing inside the workflow and update the passed entity object (`entity`) with results, status updates, timestamps, and the paginated restaurant data.
- For external entity fetching/adding (different entity models), it can be done inside the workflow if needed.
- The endpoint will no longer launch background tasks or update entity state after adding, because the workflow function handles that.

---

### Here is the fully refactored code:

```python
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
        while True:
            if next_page_token:
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

        # Extract request data, reconstruct dataclass from entity if needed
        request_data = entity.get("request_data")
        if not request_data:
            entity["status"] = "error"
            entity["error"] = "Missing request_data"
            return entity

        # Convert dict to SearchRequest dataclass
        # Because of nested dataclasses, we reconstruct manually
        loc = request_data.get("location")
        location = Location(latitude=loc["latitude"], longitude=loc["longitude"])
        radius = request_data.get("radius")
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
        search_request = SearchRequest(location=location, radius=radius, filters=filters, pagination=pagination)

        # Fetch, filter, format restaurants from Google Places API
        raw_restaurants = await fetch_restaurants_from_google(
            search_request.location, search_request.radius, search_request.filters
        )
        total_results = len(raw_restaurants)
        all_restaurants = [format_restaurant(r) for r in raw_restaurants]

        # Paginate results for current page
        page = search_request.pagination.page or 1
        page_size = search_request.pagination.page_size or DEFAULT_PAGE_SIZE
        restaurants_page = paginate(all_restaurants, page, page_size)

        # Update entity state - modify entity dict directly
        entity["status"] = "completed"
        entity["completedAt"] = datetime.utcnow().isoformat()
        entity["total_results"] = total_results
        entity["all_restaurants"] = all_restaurants
        entity["current_page"] = page
        entity["page_size"] = page_size
        entity["restaurants_page"] = restaurants_page

        # Add processed timestamp
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

    # Prepare initial entity with minimal info and status processing
    initial_entity = {
        "search_id": search_id,
        "status": "processing",
        "requestedAt": requested_at,
        "request_data": asdict(data),
    }
    try:
        # Add entity with workflow function that will do full processing asynchronously before persisting
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

    # Return search_id immediately, no background task needed, processing done in workflow
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

    # Return paginated restaurants page from stored entity data
    restaurants_page = entity_data.get("restaurants_page", [])
    total_results = entity_data.get("total_results", 0)

    # Optional: if client requests a different page than stored, paginate again
    # But this is read-only and entity_data might not have all_restaurants
    # Just return stored page for simplicity

    response = {
        "search_id": search_id,
        "total_results": total_results,
        "page": entity_data.get("current_page", 1),
        "page_size": entity_data.get("page_size", DEFAULT_PAGE_SIZE),
        "restaurants": restaurants_page,
    }
    return jsonify(response)


if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
```

---

### Explanation of changes:

- **`process_search_result` workflow**:  
  - Takes the entity dict, extracts request data, performs the entire search & filtering & formatting logic.
  - Updates the entity dict with status, metadata, and paginated results before persistence.
  - Handles errors by updating entity state with error info.
  - No external update calls to the same entity model (avoids recursion), only modifies the passed entity dict.
- **Endpoint `/api/search-restaurants`**:  
  - Simply creates an initial entity with `status=processing` and request data.
  - Calls `entity_service.add_item` with the workflow function.
  - Returns immediately with `search_id`.
- **Endpoint `/api/search-results/<search_id>`**:  
  - Retrieves persisted entity from `entity_service`.
  - Returns status and paginated results from stored entity data.
- **No background tasks or external updates are needed** because workflow handles all async processing before the entity is persisted.

---

This design fully leverages the new workflow system to encapsulate all async processing and state management, keeping controllers clean and making the app more robust and maintainable.

If you want, I can also help you test or further improve this!