from dataclasses import dataclass, field
from typing import Optional, List, Dict
import asyncio
import logging
from datetime import datetime

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# In-memory cache to mock persistence: {search_id: {"status": str, "flights": list, "requested_at": datetime}}
search_cache = {}

AIRPORT_GAP_BASE = "https://airportgap.dev-tester.com/api"

AVIATIONSTACK_API_KEY = "YOUR_AVIATIONSTACK_API_KEY"  # TODO: Replace with your real key
AVIATIONSTACK_BASE = "http://api.aviationstack.com/v1"


@dataclass
class Passengers:
    adults: int = 1
    children: int = 0
    infants: int = 0


@dataclass
class Filters:
    airlines: Optional[List[str]] = field(default_factory=list)
    max_price: Optional[float] = None
    stops: Optional[int] = None


@dataclass
class FlightSearchRequest:
    departure_airport: str
    arrival_airport: str
    departure_date: str
    return_date: Optional[str] = None
    passengers: Passengers = field(default_factory=Passengers)
    filters: Optional[Filters] = None
    sort_by: Optional[str] = None


async def fetch_airport_info(iata_code: str, client: httpx.AsyncClient) -> Optional[dict]:
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
    passengers: Passengers,
    client: httpx.AsyncClient,
) -> list:
    try:
        params = {
            "access_key": AVIATIONSTACK_API_KEY,
            "dep_iata": departure_iata,
            "arr_iata": arrival_iata,
        }
        url = f"{AVIATIONSTACK_BASE}/flights"
        resp = await client.get(url, params=params)
        if resp.status_code != 200:
            logger.error(f"Flight API returned status {resp.status_code}")
            return []

        data = resp.json()
        flights_raw = data.get("data", [])

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


async def process_search(search_id: str, data: FlightSearchRequest):
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            dep_airport = await fetch_airport_info(data.departure_airport, client)
            arr_airport = await fetch_airport_info(data.arrival_airport, client)
            if not dep_airport or not arr_airport:
                search_cache[search_id]["status"] = "error"
                search_cache[search_id]["message"] = "Invalid departure or arrival airport code."
                logger.info(f"Invalid airports for search_id {search_id}")
                return

            flights = await fetch_flights(
                data.departure_airport,
                data.arrival_airport,
                data.departure_date,
                data.passengers,
                client,
            )

            if not flights:
                search_cache[search_id]["status"] = "no_results"
                search_cache[search_id]["message"] = "No flights found for the given criteria."
                logger.info(f"No flights found for search_id {search_id}")
                return

            search_cache[search_id]["status"] = "completed"
            search_cache[search_id]["flights"] = flights
            logger.info(f"Search {search_id} completed with {len(flights)} flights.")

    except Exception as e:
        logger.exception(f"Exception in processing search {search_id}: {e}")
        search_cache[search_id]["status"] = "error"
        search_cache[search_id]["message"] = "Internal error during flight search processing."


@app.route("/api/flights/search", methods=["POST"])
@validate_request(FlightSearchRequest)  # validation last in POST route - issue workaround
async def search_flights(data: FlightSearchRequest):
    search_id = f"search_{int(datetime.utcnow().timestamp() * 1000)}"
    search_cache[search_id] = {
        "status": "processing",
        "flights": [],
        "requested_at": datetime.utcnow(),
    }

    asyncio.create_task(process_search(search_id, data))

    return jsonify({"search_id": search_id, "status": "processing", "result_count": 0})


# GET route with no request body - no validation needed
@app.route("/api/flights/search/<string:search_id>", methods=["GET"])
async def get_search_results(search_id: str):
    record = search_cache.get(search_id)
    if not record:
        return (
            jsonify({"search_id": search_id, "flights": [], "status": "error", "message": "Search ID not found"}),
            404,
        )

    if record["status"] == "processing":
        return jsonify(
            {"search_id": search_id, "flights": [], "status": "processing", "message": "Search is still processing"}
        )

    if record["status"] in ("error", "no_results"):
        return jsonify(
            {
                "search_id": search_id,
                "flights": [],
                "status": record["status"],
                "message": record.get("message", ""),
            }
        )

    return jsonify({"search_id": search_id, "flights": record.get("flights", []), "status": "completed"})


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