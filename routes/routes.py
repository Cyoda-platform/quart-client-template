from dataclasses import dataclass
from typing import Optional, Dict, Any, List
import asyncio
import logging
from datetime import datetime

import httpx
from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request

from app_init.app_init import BeanFactory
from common.config.config import ENTITY_VERSION

factory = BeanFactory(config={'CHAT_REPOSITORY': 'cyoda'})
entity_service = factory.get_services()['entity_service']
cyoda_auth_service = factory.get_services()["cyoda_auth_service"]

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

@dataclass
class Filters:
    genre: Optional[str] = None
    author: Optional[str] = None
    publication_year: Optional[int] = None

@dataclass
class SearchRequest:
    query: str
    filters: Filters = Filters()
    page: int = 1
    page_size: int = 20

@dataclass
class RecommendationRequest:
    limit: int = 10

OPEN_LIBRARY_SEARCH_API = "https://openlibrary.org/search.json"
OPEN_LIBRARY_COVER_URL = "https://covers.openlibrary.org/b/id/{cover_id}-M.jpg"
OPEN_LIBRARY_WORKS_API = "https://openlibrary.org{work_key}.json"

# In-memory caches for search and recommendations
book_cache: Dict[str, Dict[str, Any]] = {}
user_search_history: Dict[str, List[Dict[str, Any]]] = {}
search_count: Dict[str, int] = {}

def get_cover_url_from_doc(doc: Dict[str, Any]) -> str:
    cover_id = doc.get("cover_i")
    if cover_id:
        return OPEN_LIBRARY_COVER_URL.format(cover_id=cover_id)
    return ""

def normalize_book_doc(doc: Dict[str, Any]) -> Dict[str, Any]:
    # minimal normalization, detailed enrichment will be in workflow
    return {
        "book_id": doc.get("key", "").replace("/works/", ""),
        "title": doc.get("title", ""),
        "author": ", ".join(doc.get("author_name", [])) if doc.get("author_name") else "",
        "genre": "",  # to be enriched later
        "publication_year": doc.get("first_publish_year"),
        "cover_image": get_cover_url_from_doc(doc),
        "description": None  # to be enriched later
    }

async def fetch_work_description(work_key: str) -> Optional[str]:
    # Fetch description from works API for enrichment
    url = OPEN_LIBRARY_WORKS_API.format(work_key=work_key)
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.get(url)
            resp.raise_for_status()
            data = resp.json()
            desc = data.get("description")
            if isinstance(desc, dict):
                return desc.get("value")
            elif isinstance(desc, str):
                return desc
        except Exception as e:
            logger.warning(f"Failed to fetch description for {work_key}: {e}")
    return None

def filter_books(books: List[Dict[str, Any]], genre: Optional[str], author: Optional[str], publication_year: Optional[int]) -> List[Dict[str, Any]]:
    filtered = []
    for book in books:
        if genre and book.get("genre") and genre.lower() != book.get("genre", "").lower():
            continue
        if author and author.lower() not in book.get("author", "").lower():
            continue
        if publication_year and publication_year != book.get("publication_year"):
            continue
        filtered.append(book)
    return filtered

async def calculate_recommendations(user_id: str, limit: int) -> List[Dict[str, Any]]:
    history = user_search_history.get(user_id, [])
    if not history:
        top_ids = sorted(search_count, key=lambda k: search_count[k], reverse=True)[:limit]
        return [book_cache[i] for i in top_ids if i in book_cache]
    authors = {f["filters"]["author"].lower() for f in history if f["filters"].get("author")}
    genres = {f["filters"]["genre"].lower() for f in history if f["filters"].get("genre")}
    candidates = []
    for bid, book in book_cache.items():
        a = book.get("author", "").lower()
        g = book.get("genre", "").lower()
        if (authors and any(x in a for x in authors)) or (genres and g in genres):
            candidates.append(book)
    sorted_cand = sorted(candidates, key=lambda b: search_count.get(b["book_id"], 0), reverse=True)
    return sorted_cand[:limit]

@app.route("/api/books/search", methods=["POST"])
@validate_request(SearchRequest)
async def search_books(data: SearchRequest):
    if not data.query:
        return jsonify({"error": "Query parameter is required"}), 400
    user_id = request.headers.get("X-User-Id", "anonymous")

    # Use the in-memory cache for searching
    # Filter cached books by query and filters
    # Note: This is a simplified search, can be replaced with a real search backend

    # Filter by query in title or author (case insensitive)
    filtered_books = [
        book for book in book_cache.values()
        if data.query.lower() in book.get("title", "").lower()
        or data.query.lower() in book.get("author", "").lower()
    ]

    # Apply filters
    filtered_books = filter_books(filtered_books, data.filters.genre, data.filters.author, data.filters.publication_year)

    # Pagination
    start = (data.page - 1) * data.page_size
    end = start + data.page_size
    page_books = filtered_books[start:end]

    # Track user search history and increase search counts
    user_history = user_search_history.setdefault(user_id, [])
    user_history.append({"query": data.query, "filters": vars(data.filters), "timestamp": datetime.utcnow().isoformat()})
    for b in page_books:
        search_count[b["book_id"]] = search_count.get(b["book_id"], 0) + 1

    return jsonify({
        "results": page_books,
        "total_results": len(filtered_books),
        "page": data.page,
        "page_size": data.page_size
    })

@app.route("/api/books/<string:book_id>", methods=["GET"])
async def get_book_details(book_id):
    try:
        item = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model="book",
            entity_version=ENTITY_VERSION,
            technical_id=book_id
        )
        if not item:
            return jsonify({"error": "Book not found"}), 404
        return jsonify(item)
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Internal Server Error"}), 500

@app.route("/api/users/<string:user_id>/search-history", methods=["GET"])
async def get_search_history(user_id):
    return jsonify({"user_id": user_id, "search_history": user_search_history.get(user_id, [])})

@app.route("/api/users/<string:user_id>/recommendations", methods=["POST"])
@validate_request(RecommendationRequest)
async def get_recommendations(user_id, data: RecommendationRequest):
    recs = await calculate_recommendations(user_id, data.limit)
    return jsonify({"user_id": user_id, "recommendations": recs})

@app.route("/api/reports/weekly", methods=["GET"])
async def get_weekly_report():
    most = sorted(search_count.items(), key=lambda x: x[1], reverse=True)[:10]
    most_list = [{"book_id": bid, "title": book_cache[bid]["title"], "search_count": cnt} for bid, cnt in most if bid in book_cache]

    genre_count: Dict[str, int] = {}
    author_count: Dict[str, int] = {}
    for hist in user_search_history.values():
        for e in hist:
            f = e["filters"]
            if f.get("genre"):
                genre_count[f["genre"]] = genre_count.get(f["genre"], 0) + 1
            if f.get("author"):
                author_count[f["author"]] = author_count.get(f["author"], 0) + 1

    top_genres = [g for g, _ in sorted(genre_count.items(), key=lambda x: x[1], reverse=True)[:5]]
    top_authors = [a for a, _ in sorted(author_count.items(), key=lambda x: x[1], reverse=True)[:5]]
    return jsonify({
        "report_date": datetime.utcnow().isoformat(),
        "most_searched_books": most_list,
        "user_preferences_summary": {
            "top_genres": top_genres,
            "top_authors": top_authors
        }
    })

# Workflow function applied on 'book' entity before persistence
async def process_book(entity: Dict[str, Any]) -> None:
    """
    This workflow enriches the book entity, updates cache and search counts.
    It fetches detailed description asynchronously and adds timestamp.
    """

    entity["processed_at"] = datetime.utcnow().isoformat()

    # Fetch and enrich description (async fetch)
    work_key = f"/works/{entity.get('book_id')}"
    description = await fetch_work_description(work_key)
    if description:
        entity["description"] = description

    # Example: You could also enrich genre here by fetching other sources or logic
    # For demo, we leave genre empty or as is

    # Update in-memory caches (allowed since these are not persistent entities)
    book_cache[entity["book_id"]] = entity
    # Initialize search count if not present
    if entity["book_id"] not in search_count:
        search_count[entity["book_id"]] = 0

@app.route("/api/ingestion/daily", methods=["POST"])
async def trigger_daily_ingestion():
    """
    Fetch raw book data from Open Library and add them to entity service with workflow enrichment.
    """

    async def ingestion_task():
        logger.info("Starting daily ingestion")
        try:
            # Fetch raw data (no enrichment here)
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(OPEN_LIBRARY_SEARCH_API, params={"q": "programming", "page": 1, "limit": 50})
                resp.raise_for_status()
                raw = resp.json()

            docs = raw.get("docs", [])
            # Normalize minimally, detailed enrichment in workflow
            books = [normalize_book_doc(d) for d in docs]

            # Add entities without workflow enrichment
            tasks = []
            for book in books:
                tasks.append(entity_service.add_item(
                    token=cyoda_auth_service,
                    entity_model="book",
                    entity_version=ENTITY_VERSION,
                    entity=book
                ))
            # Await all add_item calls concurrently
            await asyncio.gather(*tasks)

            logger.info(f"Daily ingestion updated {len(books)} books")

        except Exception as exc:
            logger.exception(f"Error during daily ingestion: {exc}")

    asyncio.create_task(ingestion_task())
    return jsonify({"status": "processing", "message": "Daily ingestion started"}), 202


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s", stream=sys.stdout)
    app.run(use_reloader=False, debug=True, host="0.0.0.0", port=8000, threaded=True)
