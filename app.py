from common.grpc_client.grpc_client import grpc_stream
from datetime import datetime
import asyncio
import aiohttp
from dataclasses import dataclass
from quart import Quart, jsonify
from quart_schema import QuartSchema, validate_request  # Using QuartSchema as required
from common.config.config import ENTITY_VERSION
from app_init.app_init import entity_service, cyoda_token
from common.repository.cyoda.cyoda_init import init_cyoda

app = Quart(__name__)
QuartSchema(app)  # One-liner setup for QuartSchema

SUPPLEMENTARY_API_URL = "https://api.practicesoftwaretesting.com/supplementary/info"
EXTERNAL_API_URL = "https://api.practicesoftwaretesting.com/categories/tree"

# Startup hook to initialize external service
@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)
    app.background_task = asyncio.create_task(grpc_stream(cyoda_token))

@app.after_serving
async def shutdown():
    app.background_task.cancel()
    await app.background_task

# Request dataclasses for validation
@dataclass
class FetchCategoriesRequest:
    refresh: bool = False  # Optional refresh flag

@dataclass
class SearchRequest:
    query: str

# Helper function to recursively search through the category tree
def find_category(categories, query):
    # Ensure categories is iterable
    if isinstance(categories, dict):
        categories = [categories]
    for category in categories:
        if isinstance(category, dict):
            # Compare both name (case-insensitive) and id
            if (category.get("name", "").lower() == query.lower() or 
                category.get("id", "") == query):
                return category
            # Check if sub_categories exist and recurse into them
            sub_cats = category.get("sub_categories")
            if sub_cats:
                result = find_category(sub_cats, query)
                if result:
                    return result
    return None

# Endpoint to fetch categories from external API and store them via entity_service
@app.route("/api/categories/fetch", methods=["POST"])
@validate_request(FetchCategoriesRequest)
async def fetch_categories(data: FetchCategoriesRequest):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(EXTERNAL_API_URL, timeout=10) as resp:
                if resp.status != 200:
                    return jsonify({"status": "error", "message": "Failed to fetch data from external API"}), 500
                try:
                    raw_data = await resp.json()
                except Exception as json_exc:
                    return jsonify({"status": "error", "message": f"JSON decode error: {json_exc}"}), 500

        # In case of additional transformations, perform them here.
        transformed_data = raw_data

        # Persist the entity with the workflow function applied.
        entity_id = await entity_service.add_item(
            token=cyoda_token,
            entity_model="categories",
            entity_version=ENTITY_VERSION,  # always use this constant
            entity=transformed_data,  # the validated/transformed data object
            )
        # Return only the technical id; the stored data can be retrieved by another endpoint.
        return jsonify({"status": "success", "id": entity_id}), 200

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# Endpoint to retrieve stored categories via external service
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

# Endpoint to search through the stored categories data
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

        # Iterate over all stored items in case multiple category trees exist.
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