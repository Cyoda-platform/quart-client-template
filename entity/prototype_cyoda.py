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

def get_cover_url_from_doc(doc: Dict[str, Any]) -> str:
    cover_id = doc.get("cover_i")
    if cover_id:
        return OPEN_LIBRARY_COVER_URL.format(cover_id=cover_id)
    return ""

def normalize_book_doc(doc: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "book_id": doc.get("key", "").replace("/works/", ""),
        "title": doc.get("title", ""),
        "author": ", ".join(doc.get("author_name", [])) if doc.get("author_name") else "",
        "genre": "",  # TODO: Open Library API lacks genre info
        "publication_year": doc.get("first_publish_year"),
        "cover_image": get_cover_url_from_doc(doc),
        "description": None  # TODO: implement description fetch
    }

async def fetch_books_from_openlibrary(query: str, page: int, page_size: int) -> Dict[str, Any]:
    params = {"q": query, "page": page, "limit": page_size}
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.get(OPEN_LIBRARY_SEARCH_API, params=params)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.exception(f"Error fetching from Open Library API: {e}")
            return {"docs": [], "numFound": 0}

def filter_books(books: List[Dict[str, Any]], genre: str, author: str, publication_year: int) -> List[Dict[str, Any]]:
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
    # Remove in-memory cache update because data is now in entity_service
    # but keep it here if needed for recommendation logic
    # We'll still update local cache for recommendation and search_count tracking
    for book in books:
        book_cache[book["book_id"]] = book

# Keep local caches for recommendation and search count as business logic
book_cache: Dict[str, Dict[str, Any]] = {}
user_search_history: Dict[str, List[Dict[str, Any]]] = {}
search_count: Dict[str, int] = {}

async def process_search(user_id: str, query: str, filters: Filters, page: int, page_size: int):
    raw = await fetch_books_from_openlibrary(query, page, page_size)
    docs = raw.get("docs", [])
    total = raw.get("numFound", 0)
    normalized = [normalize_book_doc(d) for d in docs]
    await update_book_cache(normalized)
    filtered = filter_books(normalized, filters.genre, filters.author, filters.publication_year)
    user_history = user_search_history.setdefault(user_id, [])
    user_history.append({"query": query, "filters": vars(filters), "timestamp": datetime.utcnow().isoformat()})
    for b in filtered:
        search_count[b["book_id"]] = search_count.get(b["book_id"], 0) + 1
    return filtered, total

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
    books, total = await process_search(user_id, data.query, data.filters, data.page, data.page_size)
    return jsonify({"results": books, "total_results": total, "page": data.page, "page_size": data.page_size})

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
    # user search history still local cache for now
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
    return jsonify({"report_date": datetime.utcnow().isoformat(),
                    "most_searched_books": most_list,
                    "user_preferences_summary": {"top_genres": top_genres, "top_authors": top_authors}})

@app.route("/api/ingestion/daily", methods=["POST"])
async def trigger_daily_ingestion():
    async def task():
        logger.info("Starting daily ingestion")
        try:
            raw = await fetch_books_from_openlibrary("programming", 1, 50)
            docs = raw.get("docs", [])
            books = [normalize_book_doc(d) for d in docs]
            # replace local cache update with entity_service add_item calls
            for book in books:
                try:
                    await entity_service.add_item(
                        token=cyoda_auth_service,
                        entity_model="book",
                        entity_version=ENTITY_VERSION,
                        entity=book
                    )
                except Exception as e:
                    logger.exception(f"Failed to add book {book.get('book_id')}: {e}")
            # Also update local cache for recommendations and search_count
            await update_book_cache(books)
            logger.info(f"Daily ingestion updated {len(books)} books")
        except Exception as e:
            logger.exception(f"Error in ingestion: {e}")
    asyncio.create_task(task())
    return jsonify({"status": "processing", "message": "Daily ingestion started"}), 202

if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s", stream=sys.stdout)
    app.run(use_reloader=False, debug=True, host="0.0.0.0", port=8000, threaded=True)