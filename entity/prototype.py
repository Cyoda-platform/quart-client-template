```python
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, List

import httpx
from quart import Quart, request, jsonify
from quart_schema import QuartSchema

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# In-memory caches for prototype purposes
book_cache: Dict[str, Dict[str, Any]] = {}  # book_id -> book data
user_search_history: Dict[str, List[Dict[str, Any]]] = {}  # user_id -> list of search queries
search_count: Dict[str, int] = {}  # book_id -> count of searches

# Constants for Open Library API
OPEN_LIBRARY_SEARCH_API = "https://openlibrary.org/search.json"
OPEN_LIBRARY_COVER_URL = "https://covers.openlibrary.org/b/id/{cover_id}-M.jpg"

# Utility functions


def get_cover_url_from_doc(doc: Dict[str, Any]) -> str:
    cover_id = doc.get("cover_i")
    if cover_id:
        return OPEN_LIBRARY_COVER_URL.format(cover_id=cover_id)
    return ""


def normalize_book_doc(doc: Dict[str, Any]) -> Dict[str, Any]:
    # Normalize relevant book data from Open Library doc
    return {
        "book_id": doc.get("key", "").replace("/works/", ""),
        "title": doc.get("title", ""),
        "author": ", ".join(doc.get("author_name", [])) if doc.get("author_name") else "",
        "genre": "",  # TODO: Open Library search API does not provide genre directly
        "publication_year": doc.get("first_publish_year"),
        "cover_image": get_cover_url_from_doc(doc),
        "description": None  # TODO: Fetch detailed description if needed via separate API call
    }


async def fetch_books_from_openlibrary(
    query: str, page: int = 1, page_size: int = 20
) -> Dict[str, Any]:
    params = {
        "q": query,
        "page": page,
        "limit": page_size,
    }
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.get(OPEN_LIBRARY_SEARCH_API, params=params)
            resp.raise_for_status()
            data = resp.json()
            return data
        except Exception as e:
            logger.exception(f"Error fetching from Open Library API: {e}")
            return {"docs": [], "numFound": 0}


def filter_books(
    books: List[Dict[str, Any]],
    genre: str = None,
    author: str = None,
    publication_year: int = None,
) -> List[Dict[str, Any]]:
    # Genre filtering not implemented due to data unavailability
    filtered = []
    for book in books:
        if genre and book.get("genre") != genre:
            continue
        if author and author.lower() not in book.get("author", "").lower():
            continue
        if publication_year and book.get("publication_year") != publication_year:
            continue
        filtered.append(book)
    return filtered


async def update_book_cache(books: List[Dict[str, Any]]):
    for book in books:
        book_cache[book["book_id"]] = book


async def process_search(user_id: str, query: str, filters: Dict[str, Any], page: int, page_size: int):
    # Fetch from Open Library
    raw_data = await fetch_books_from_openlibrary(query, page, page_size)
    docs = raw_data.get("docs", [])
    total_results = raw_data.get("numFound", 0)

    # Normalize
    normalized_books = [normalize_book_doc(doc) for doc in docs]

    # Update cache
    await update_book_cache(normalized_books)

    # Filter locally
    filtered_books = filter_books(
        normalized_books,
        genre=filters.get("genre"),
        author=filters.get("author"),
        publication_year=filters.get("publication_year"),
    )

    # Update user search history
    user_history = user_search_history.setdefault(user_id, [])
    user_history.append(
        {
            "query": query,
            "filters": filters,
            "timestamp": datetime.utcnow().isoformat(),
        }
    )

    # Update search counts
    for book in filtered_books:
        search_count[book["book_id"]] = search_count.get(book["book_id"], 0) + 1

    return filtered_books, total_results


async def calculate_recommendations(user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
    # Simple recommendation: top searched books matching user's previous searched authors or genres

    history = user_search_history.get(user_id, [])
    if not history:
        # Fallback: top searched books overall
        top_books_ids = sorted(
            search_count.keys(), key=lambda k: search_count[k], reverse=True
        )[:limit]
        return [book_cache.get(book_id) for book_id in top_books_ids if book_cache.get(book_id)]

    # Collect authors and genres from user history
    authors_searched = set()
    genres_searched = set()
    for entry in history:
        filters = entry.get("filters", {})
        if filters.get("author"):
            authors_searched.add(filters["author"].lower())
        if filters.get("genre"):
            genres_searched.add(filters["genre"].lower())

    # Recommend books that match authors or genres from cache, sorted by popularity
    candidates = []
    for book_id, book in book_cache.items():
        if not book:
            continue
        author = book.get("author", "").lower()
        genre = book.get("genre", "").lower()
        if (authors_searched and any(a in author for a in authors_searched)) or (
            genres_searched and genre in genres_searched
        ):
            candidates.append(book)

    # Sort candidates by search_count descending
    candidates_sorted = sorted(
        candidates, key=lambda b: search_count.get(b["book_id"], 0), reverse=True
    )

    # Limit results
    return candidates_sorted[:limit]


# API endpoints


@app.route("/api/books/search", methods=["POST"])
async def search_books():
    data = await request.get_json()
    query = data.get("query", "").strip()
    filters = data.get("filters", {}) or {}
    page = data.get("page", 1)
    page_size = data.get("page_size", 20)

    if not query:
        return jsonify({"error": "Query parameter is required"}), 400

    # For prototype, user_id is fixed or from header (TODO: authenticate user)
    user_id = request.headers.get("X-User-Id", "anonymous")

    filtered_books, total_results = await process_search(user_id, query, filters, page, page_size)

    response = {
        "results": filtered_books,
        "total_results": total_results,
        "page": page,
        "page_size": page_size,
    }
    return jsonify(response)


@app.route("/api/books/<book_id>", methods=["GET"])
async def get_book_details(book_id):
    book = book_cache.get(book_id)
    if not book:
        return jsonify({"error": "Book not found"}), 404
    return jsonify(book)


@app.route("/api/users/<user_id>/search-history", methods=["GET"])
async def get_search_history(user_id):
    history = user_search_history.get(user_id, [])
    return jsonify({"user_id": user_id, "search_history": history})


@app.route("/api/users/<user_id>/recommendations", methods=["POST"])
async def get_recommendations(user_id):
    data = await request.get_json() or {}
    limit = data.get("limit", 10)
    recommendations = await calculate_recommendations(user_id, limit)
    return jsonify({"user_id": user_id, "recommendations": recommendations})


@app.route("/api/reports/weekly", methods=["GET"])
async def get_weekly_report():
    # For prototype, generate a simple report from current search_count and user_search_history

    most_searched_books = sorted(
        search_count.items(), key=lambda x: x[1], reverse=True
    )[:10]
    most_searched_books_list = []
    for book_id, count in most_searched_books:
        book = book_cache.get(book_id)
        if book:
            most_searched_books_list.append(
                {"book_id": book_id, "title": book.get("title", ""), "search_count": count}
            )

    # Aggregate user preferences (genres and authors from history)
    genre_counter: Dict[str, int] = {}
    author_counter: Dict[str, int] = {}

    for history in user_search_history.values():
        for entry in history:
            filters = entry.get("filters", {})
            genre = filters.get("genre")
            if genre:
                genre_counter[genre] = genre_counter.get(genre, 0) + 1
            author = filters.get("author")
            if author:
                author_counter[author] = author_counter.get(author, 0) + 1

    top_genres = sorted(genre_counter.items(), key=lambda x: x[1], reverse=True)
    top_authors = sorted(author_counter.items(), key=lambda x: x[1], reverse=True)

    response = {
        "report_date": datetime.utcnow().isoformat(),
        "most_searched_books": most_searched_books_list,
        "user_preferences_summary": {
            "top_genres": [g[0] for g in top_genres[:5]],
            "top_authors": [a[0] for a in top_authors[:5]],
        },
    }
    return jsonify(response)


@app.route("/api/ingestion/daily", methods=["POST"])
async def trigger_daily_ingestion():
    # For prototype, simulate ingestion by fetching a fixed popular query and updating cache

    async def ingestion_task():
        logger.info("Starting daily ingestion task")
        try:
            # Example: fetch "programming" books first page
            raw_data = await fetch_books_from_openlibrary("programming", page=1, page_size=50)
            docs = raw_data.get("docs", [])
            normalized_books = [normalize_book_doc(doc) for doc in docs]
            await update_book_cache(normalized_books)
            logger.info(f"Daily ingestion updated {len(normalized_books)} books")
        except Exception as e:
            logger.exception(f"Error in daily ingestion: {e}")

    # Fire and forget
    asyncio.create_task(ingestion_task())

    return jsonify({"status": "processing", "message": "Daily ingestion started"}), 202


if __name__ == "__main__":
    import logging.config
    import sys

    # Basic console logging config
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        stream=sys.stdout,
    )

    app.run(use_reloader=False, debug=True, host="0.0.0.0", port=8000, threaded=True)
```
