```python
import asyncio
import logging
from datetime import datetime
from typing import Optional

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# In-memory cache to mock persistence: {search_id: {"status": str, "flights": list, "requested_at": datetime}}
search_cache = {}

# Airport Gap API base URL and key (replace with your API key if needed)
AIRPORT_GAP_BASE = "https://airportgap.dev-tester.com/api"
# TODO: For real usage, add API key or auth if required by Airport Gap

# Placeholder for flight search external API
# Airport Gap API does NOT provide real flight schedules/pricing.
# For prototype, use AviationStack API free tier for flight info simulation.
# You must get an API key at https://aviationstack.com/
AVIATIONSTACK_API_KEY = "YOUR_AVIATIONSTACK_API_KEY"  # TODO: Replace with your real key
AVIATIONSTACK_BASE = "http://api.aviationstack.com/v1"

# NOTE: AviationStack free tier might have limitations and delayed data,
# so this prototype aims to mimic flight search UX based on this.


async def fetch_airport_info(iata_code: str, client: httpx.AsyncClient) -> Optional[dict]:
    """
    Validate airport IATA code using Airport Gap API
    """
    try:
        url = f"{AIRPORT_GAP_BASE}/airports/{iata_code}"
        resp = await client.get(url)
        if resp.status_code == 200:
            return resp.json()
        else:
            logger.info(f"Airport {iata_code} not found in Airport Gap API.")
            return None
    except Exception as e:
        logger.exception(f"Failed to fetch airport info for {iata_code}: {e}")
        return None


async def fetch_flights(
    departure_iata: str,
    arrival_iata: str,
    departure_date: str,
    passengers: dict,
    client: httpx.AsyncClient,
) -> list:
    """
    Fetch flights from external API (AviationStack) for prototype.
    This is a simplification: AviationStack free tier doesn't support date or passenger filtering.
    We'll filter manually by departure airport and arrival airport codes.
    """
    try:
        params = {
            "access_key": AVIATIONSTACK_API_KEY,
            "dep_iata": departure_iata,
            "arr_iata": arrival_iata,
            # No direct date filter supported in free tier - TODO: improve with better API
        }
        url = f"{AVIATIONSTACK_BASE}/flights"
        resp = await client.get(url, params=params)
        if resp.status_code != 200:
            logger.error(f"Flight API returned status {resp.status_code}")
            return []

        data = resp.json()
        flights_raw = data.get("data", [])

        # Filter flights by departure_date (approximate, as API returns timestamps)
        filtered_flights = []
        for f in flights_raw:
            dep_time = f.get("departure", {}).get("scheduled")
            arr_time = f.get("arrival", {}).get("scheduled")
            if not dep_time or not arr_time:
                continue
            try:
                dep_date = dep_time.split("T")[0]
                if dep_date != departure_date:
                    continue
            except Exception:
                continue

            # Build flight info model
            flight = {
                "flight_number": f.get("flight", {}).get("iata") or f.get("flight", {}).get("number"),
                "airline": f.get("airline", {}).get("name"),
                "departure_airport": departure_iata,
                "arrival_airport": arrival_iata,
                "departure_time": dep_time,
                "arrival_time": arr_time,
                "price": None,  # TODO: No pricing info from this API; leave None or mock
                "duration": None,  # TODO: Could calculate duration from times if desired
                "stops": 0,  # TODO: No stops info here, assume direct flights only for prototype
            }
            filtered_flights.append(flight)

        return filtered_flights

    except Exception as e:
        logger.exception(f"Error fetching flights: {e}")
        return []


async def process_search(search_id: str, data: dict):
    """
    Background task to validate airports, query flights, store results.
    """
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            # Validate airports
            dep_airport = await fetch_airport_info(data["departure_airport"], client)
            arr_airport = await fetch_airport_info(data["arrival_airport"], client)
            if not dep_airport or not arr_airport:
                search_cache[search_id]["status"] = "error"
                search_cache[search_id]["message"] = "Invalid departure or arrival airport code."
                logger.info(f"Invalid airports for search_id {search_id}")
                return

            # Fetch flights
            flights = await fetch_flights(
                data["departure_airport"],
                data["arrival_airport"],
                data["departure_date"],
                data.get("passengers", {"adults": 1}),
                client,
            )

            if not flights:
                search_cache[search_id]["status"] = "no_results"
                search_cache[search_id]["message"] = "No flights found for the given criteria."
                logger.info(f"No flights found for search_id {search_id}")
                return

            # Store results
            search_cache[search_id]["status"] = "completed"
            search_cache[search_id]["flights"] = flights
            logger.info(f"Search {search_id} completed with {len(flights)} flights.")

    except Exception as e:
        logger.exception(f"Exception in processing search {search_id}: {e}")
        search_cache[search_id]["status"] = "error"
        search_cache[search_id]["message"] = "Internal error during flight search processing."


@app.route("/api/flights/search", methods=["POST"])
async def search_flights():
    data = await request.get_json(force=True)

    # Basic input validation (minimal for prototype)
    required_fields = ["departure_airport", "arrival_airport", "departure_date", "passengers"]
    for field in required_fields:
        if field not in data:
            return jsonify({"search_id": None, "status": "error", "message": f"Missing field: {field}"}), 400

    search_id = f"search_{int(datetime.utcnow().timestamp() * 1000)}"
    search_cache[search_id] = {
        "status": "processing",
        "flights": [],
        "requested_at": datetime.utcnow(),
    }

    # Fire and forget processing task
    asyncio.create_task(process_search(search_id, data))

    return jsonify({"search_id": search_id, "status": "processing", "result_count": 0})


@app.route("/api/flights/search/<string:search_id>", methods=["GET"])
async def get_search_results(search_id: str):
    record = search_cache.get(search_id)
    if not record:
        return jsonify({"search_id": search_id, "flights": [], "status": "error", "message": "Search ID not found"}), 404

    if record["status"] == "processing":
        return jsonify({"search_id": search_id, "flights": [], "status": "processing", "message": "Search is still processing"})

    if record["status"] in ("error", "no_results"):
        return jsonify(
            {
                "search_id": search_id,
                "flights": [],
                "status": record["status"],
                "message": record.get("message", ""),
            }
        )

    # Completed: return flights list
    return jsonify(
        {
            "search_id": search_id,
            "flights": record.get("flights", []),
            "status": "completed",
        }
    )


if __name__ == "__main__":
    import sys
    import logging.config

    logging.basicConfig(
        stream=sys.stdout,
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    app.run(use_reloader=False, debug=True, host="0.0.0.0", port=8000, threaded=True)
```
