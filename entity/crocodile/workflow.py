from quart import Quart, request, jsonify
import httpx
import logging
from dataclasses import dataclass
from quart_schema import QuartSchema, validate_request, validate_querystring

app = Quart(__name__)
QuartSchema(app)  # Initialize QuartSchema for future use

# Set up logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

@dataclass
class CrocodileIngest:
    refresh: bool = False  # optional field for ingestion

@dataclass
class CrocodileQuery:
    name: str = None  # optional
    sex: str = None  # optional
    min_age: int = None  # optional
    max_age: int = None  # optional

async def fetch_crocodile_data():
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get("https://test-api.k6.io/public/crocodiles/")
            response.raise_for_status()  # Raise an error for bad responses
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error occurred: {e}")
            return []
        except Exception as e:
            logger.error(f"An error occurred while fetching crocodile data: {e}")
            return []

@app.route('/api/crocodiles/ingest', methods=['POST'])
@validate_request(CrocodileIngest)  # Validation for POST request
async def ingest_crocodile_data(data: CrocodileIngest):
    try:
        total_records = 0
        ingested_data = await fetch_crocodile_data()

        # Process each crocodile entity
        for crocodile in ingested_data:
            processed_crocodile = await process_crocodile(crocodile)
            # Store processed crocodile in cache or similar
            # TODO: Add to local cache here if needed

        total_records = len(ingested_data)
        logger.info(f"Ingested {total_records} crocodile records.")
        return jsonify({"message": "Data ingestion successful", "total_records": total_records}), 200
    except Exception as e:
        logger.exception("Error during data ingestion")
        return jsonify({"error": "Data ingestion failed"}), 500

@app.route('/api/crocodiles/', methods=['GET'])
@validate_querystring(CrocodileQuery)  # Validation for GET request
async def get_crocodiles():
    name = request.args.get('name')
    sex = request.args.get('sex')
    min_age = request.args.get('min_age', type=int)
    max_age = request.args.get('max_age', type=int)

    # Filter crocodile data from local cache
    filtered_crocodiles = []  # TODO: Replace with actual cached data
    return jsonify({"crocodiles": filtered_crocodiles}), 200

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)