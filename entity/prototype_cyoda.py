from datetime import datetime
import asyncio
import aiohttp
from dataclasses import dataclass
from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request  # Using QuartSchema as required
from common.config.config import ENTITY_VERSION
from app_init.app_init import entity_service, cyoda_token
from common.repository.cyoda.cyoda_init import init_cyoda

app = Quart(__name__)
QuartSchema(app)  # One-liner setup for QuartSchema

# Startup hook to initialize external service
@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)

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

# Endpoint to fetch categories from external API and store them via entity_service
@app.route("/api/categories/fetch", methods=["POST"])
@validate_request(FetchCategoriesRequest)
async def fetch_categories(data: FetchCategoriesRequest):
    refresh = data.refresh

    # In this refactored version we do not use a local cache.
    # Always fetch from the external API and add as a new item via entity_service.
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(EXTERNAL_API_URL) as resp:
                if resp.status != 200:
                    return jsonify({"status": "error", "message": "Failed to fetch data from external API"}), 500
                raw_data = await resp.json()

        # TODO: Perform any additional transformation if necessary.
        # For now, assume that the external API data is already in a hierarchical format.
        transformed_data = raw_data

        # Add the fetched data to external persistence
        id = await entity_service.add_item(
            token=cyoda_token,
            entity_model="categories",
            entity_version=ENTITY_VERSION,  # always use this constant
            entity=transformed_data  # the validated data object
        )
        # Return only the technical id; the actual data is available via a separate endpoint
        return jsonify({"status": "success", "id": id}), 200

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# Endpoint to retrieve stored categories using the external service
@app.route("/api/categories", methods=["GET"])
async def get_categories():
    try:
        items = await entity_service.get_items(
            token=cyoda_token,
            entity_model="categories",
            entity_version=ENTITY_VERSION,
        )
        if not items:
            return jsonify({"status": "error", "message": "No category data available. Please fetch data first."}), 404
        return jsonify({"status": "success", "data": items}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# Endpoint to search through the stored categories
@app.route("/api/categories/search", methods=["POST"])
@validate_request(SearchRequest)
async def search_category(data: SearchRequest):
    query = data.query.strip()
    if not query:
        return jsonify({"status": "error", "message": "Query parameter is required."}), 400

    try:
        items = await entity_service.get_items(
            token=cyoda_token,
            entity_model="categories",
            entity_version=ENTITY_VERSION,
        )
        if not items:
            return jsonify({"status": "error", "message": "No category data available. Please fetch data first."}), 404

        # Iterate over all items in case multiple category trees are stored.
        found = None
        for item in items:
            found = find_category(item, query)
            if found:
                break

        if found:
            return jsonify({"status": "success", "data": found}), 200
        else:
            return jsonify({"status": "error", "message": "Category not found"}), 404

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)