import asyncio
import datetime
import aiohttp
from dataclasses import dataclass
from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request, validate_querystring

app = Quart(__name__)
QuartSchema(app)

# Dataclass for POST /api/categories/refresh request
@dataclass
class RefreshRequest:
    forceRefresh: bool = False

# Dataclass for POST /api/categories/search request
@dataclass
class SearchRequest:
    searchTerm: str

# Global cache for category data (mock persistence)
categories_cache = {
    "categories": None,
    "last_refresh": None,
}

# Async function to fetch external data and process it
async def process_categories(force_refresh: bool):
    # TODO: Implement caching logic and check if refresh is really needed based on force_refresh
    url = "https://api.practicesoftwaretesting.com/categories/tree"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            # TODO: Add robust error handling for HTTP request failures or non-JSON responses
            raw_data = await response.json()

    # TODO: Implement any additional transformation if the external API response requires it.
    # For this prototype, we assume the raw_data is already in the desired hierarchical format.
    transformed_data = raw_data  # Placeholder for transformation logic

    # Update the global cache. Assuming the API returns a JSON object that contains a "categories" key.
    categories_cache["categories"] = transformed_data.get("categories", [])
    categories_cache["last_refresh"] = datetime.datetime.utcnow().isoformat()

# Recursive function to search for a category by name or id within a hierarchical tree
def search_category(tree, search_term):
    for category in tree:
        # Check if search term matches the category id or appears in the category name (case-insensitive)
        if str(category.get("id", "")).lower() == search_term.lower() or search_term.lower() in category.get("name", "").lower():
            return category
        # Recursively search in subCategories if they exist
        sub_categories = category.get("subCategories", [])
        if sub_categories:
            result = search_category(sub_categories, search_term)
            if result:
                return result
    return None

@app.route("/api/categories/refresh", methods=["POST"])
@validate_request(RefreshRequest)  # For POST, validation comes after route (workaround for library issue)
async def refresh_categories(data: RefreshRequest):
    force_refresh = data.forceRefresh
    # Fire and forget the processing task.
    # In a real implementation, you might want to track and return the job status.
    asyncio.create_task(process_categories(force_refresh))
    # Return immediately to verify UX; processing happens in the background.
    return jsonify({
        "status": "success",
        "message": "Category refresh initiated"
    })

@app.route("/api/categories/search", methods=["POST"])
@validate_request(SearchRequest)  # For POST, validation comes after route (workaround for library issue)
async def search_categories(data: SearchRequest):
    search_term = data.searchTerm
    if not search_term:
        return jsonify({"status": "error", "message": "searchTerm is required"}), 400

    tree = categories_cache.get("categories")
    if not tree:
        return jsonify({
            "status": "error",
            "message": "No category data available. Please refresh first."
        }), 404

    result = search_category(tree, search_term)
    if result:
        return jsonify({"status": "success", "result": result})
    else:
        return jsonify({"status": "error", "message": "Category not found"}), 404

@app.route("/api/categories", methods=["GET"])
async def get_categories():
    tree = categories_cache.get("categories")
    if not tree:
        return jsonify({
            "status": "error",
            "message": "No category data available. Please refresh first."
        }), 404
    return jsonify({
        "status": "success",
        "categories": tree,
        "last_refresh": categories_cache.get("last_refresh")
    })

# Note: GET endpoints do not require validate_request/validate_querystring if no query parameters are expected.
# For GET requests with query parameters, validation should be placed first (workaround for library issue).

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)