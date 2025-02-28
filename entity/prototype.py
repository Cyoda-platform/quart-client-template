import asyncio
import aiohttp
from dataclasses import dataclass
from datetime import datetime
from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request  # Using QuartSchema as required

app = Quart(__name__)
QuartSchema(app)  # One-liner setup for QuartSchema

# In-memory cache for categories data
categories_cache = None

# In-memory storage for processing jobs (mock persistence)
entity_job = {}  # TODO: Replace with proper persistence mechanism

EXTERNAL_API_URL = "https://api.practicesoftwaretesting.com/categories/tree"

# Request dataclasses for validation
@dataclass
class FetchCategoriesRequest:
    refresh: bool = False  # Optional refresh flag

@dataclass
class SearchRequest:
    query: str

# Helper function to recursively search through the category tree
def find_category(categories, query):
    for category in categories:
        # Check if query matches category name (case-insensitive) or id
        if (category.get("name", "").lower() == query.lower() or 
            category.get("id", "") == query):
            return category
        # Recursively search in sub_categories if available
        if category.get("sub_categories"):
            result = find_category(category["sub_categories"], query)
            if result:
                return result
    return None

# For POST endpoints, route decorator must go first then validate_request.
# This is a workaround for an issue with the Quart-Schema library.

@app.route("/api/categories/fetch", methods=["POST"])
@validate_request(FetchCategoriesRequest)
async def fetch_categories(data: FetchCategoriesRequest):
    global categories_cache
    refresh = data.refresh

    # If cached data exists and no refresh requested, return cached data
    if categories_cache and not refresh:
        return jsonify({"status": "success", "data": categories_cache}), 200

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(EXTERNAL_API_URL) as resp:
                if resp.status != 200:
                    return jsonify({"status": "error", "message": "Failed to fetch data from external API"}), 500
                raw_data = await resp.json()

        # TODO: Perform any additional transformation if necessary.
        # For now, assume that the external API data is already in a hierarchical format.
        transformed_data = raw_data

        # Cache the transformed data
        categories_cache = transformed_data

        # Log entity job (mock pattern for fire and forget processing)
        job_id = "job_fetch_" + datetime.utcnow().isoformat()
        entity_job[job_id] = {"status": "completed", "requestedAt": datetime.utcnow().isoformat()}
        # TODO: In a real scenario, fire and forget a background task:
        # await asyncio.create_task(process_entity(entity_job, transformed_data))

        return jsonify({"status": "success", "data": transformed_data}), 200

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/api/categories", methods=["GET"])
async def get_categories():
    if categories_cache is None:
        return jsonify({"status": "error", "message": "No category data available. Please fetch data first."}), 404
    return jsonify({"status": "success", "data": categories_cache}), 200

@app.route("/api/categories/search", methods=["POST"])
@validate_request(SearchRequest)
async def search_category(data: SearchRequest):
    if categories_cache is None:
        return jsonify({"status": "error", "message": "No category data available. Please fetch data first."}), 404

    query = data.query.strip()
    if not query:
        return jsonify({"status": "error", "message": "Query parameter is required."}), 400

    # Search through the cached category data recursively
    found = find_category(categories_cache, query)
    if found:
        return jsonify({"status": "success", "data": found}), 200
    else:
        return jsonify({"status": "error", "message": "Category not found"}), 404

# TODO: Implement additional background processing tasks if required.
# async def process_entity(job_store, data):
#     # Mimic a background processing task
#     await asyncio.sleep(1)  # simulate processing delay
#     # Update job status in job_store
#     # TODO: Replace with actual processing logic.
#     pass

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)