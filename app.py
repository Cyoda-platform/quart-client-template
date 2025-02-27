from common.grpc_client.grpc_client import grpc_stream
import asyncio
import datetime
import aiohttp
from dataclasses import dataclass
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request

from common.config.config import ENTITY_VERSION
from common.repository.cyoda.cyoda_init import init_cyoda
from app_init.app_init import entity_service, cyoda_token

app = Quart(__name__)
QuartSchema(app)

# Startup initialization for cyoda service
@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)
    app.background_task = asyncio.create_task(grpc_stream(cyoda_token))

@app.after_serving
async def shutdown():
    app.background_task.cancel()
    await app.background_task
    except Exception as e:
        # Log error in production; here we simply print
        print(f"Error during cyoda initialization: {e}")
        raise

# Dataclass for POST /api/categories/refresh request
@dataclass
class RefreshRequest:
    forceRefresh: bool = False

# Dataclass for POST /api/categories/search request
@dataclass
class SearchRequest:
    searchTerm: str

# Async function to fetch external data, prepare entity, and store it using entity_service
async def process_categories(force_refresh: bool):
    url = "https://api.practicesoftwaretesting.com/categories/tree"
    raw_data = {}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=10) as response:
                if response.status != 200:
                    # Handle non-200 responses appropriately
                    raise Exception(f"Failed to fetch data. Status: {response.status}")
                raw_data = await response.json()
    except asyncio.TimeoutError:
        raise Exception("External API call timed out.")
    except Exception as e:
        raise Exception(f"Error retrieving categories: {e}")

    # Validate and transform raw_data
    categories = []
    if isinstance(raw_data, dict) and "categories" in raw_data:
        categories = raw_data.get("categories", [])
    else:
        # If structure is unexpected, log and set categories to empty list
        print("Unexpected data format received from external API.")
    
    # Build the entity to be persisted
    entity = {
        "categories": categories,
        "last_refresh": datetime.datetime.utcnow().isoformat()
    }

    try:
        # Persist the entity; workflow function will be applied before persistence.
        new_id = await entity_service.add_item(
            token=cyoda_token,
            entity_model="categories",
            entity_version=ENTITY_VERSION,
            entity=entity,
            )
    except Exception as e:
        # In production, log the persistence error
        raise Exception(f"Error storing entity: {e}")
    
    return new_id

# Helper function to recursively search for a category in the hierarchical tree
def search_category(tree, search_term):
    if not isinstance(tree, list):
        return None
    for category in tree:
        # Convert id to string for comparison and perform case-insensitive search on name
        cat_id = str(category.get("id", "")).lower()
        cat_name = category.get("name", "").lower()
        if search_term.lower() == cat_id or search_term.lower() in cat_name:
            return category
        sub_categories = category.get("subCategories", [])
        result = search_category(sub_categories, search_term)
        if result:
            return result
    return None

# Endpoint to refresh categories data by fetching from external source
@app.route("/api/categories/refresh", methods=["POST"])
@validate_request(RefreshRequest)
async def refresh_categories(data: RefreshRequest):
    try:
        new_id = await process_categories(data.forceRefresh)
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    return jsonify({
        "status": "success",
        "id": new_id
    })

# Endpoint to search categories using the stored hierarchical data
@app.route("/api/categories/search", methods=["POST"])
@validate_request(SearchRequest)
async def search_categories(data: SearchRequest):
    if not data.searchTerm:
        return jsonify({"status": "error", "message": "searchTerm is required"}), 400
    try:
        items = await entity_service.get_items(
            token=cyoda_token,
            entity_model="categories",
            entity_version=ENTITY_VERSION
        )
    except Exception as e:
        return jsonify({"status": "error", "message": f"Error retrieving data: {e}"}), 500

    if not items:
        return jsonify({
            "status": "error",
            "message": "No category data available. Please refresh first."
        }), 404

    # Assume that the latest stored item is the most relevant for search
    latest_item = items[-1]
    tree = latest_item.get("categories", [])
    result = search_category(tree, data.searchTerm)
    if result:
        return jsonify({"status": "success", "result": result})
    else:
        return jsonify({"status": "error", "message": "Category not found"}), 404

# Endpoint to return the current categories data from the external store
@app.route("/api/categories", methods=["GET"])
async def get_categories():
    try:
        items = await entity_service.get_items(
            token=cyoda_token,
            entity_model="categories",
            entity_version=ENTITY_VERSION
        )
    except Exception as e:
        return jsonify({"status": "error", "message": f"Error retrieving data: {e}"}), 500

    if not items:
        return jsonify({
            "status": "error",
            "message": "No category data available. Please refresh first."
        }), 404

    latest_item = items[-1]
    return jsonify({
        "status": "success",
        "categories": latest_item.get("categories", []),
        "last_refresh": latest_item.get("last_refresh")
    })

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)