```python
from quart import Quart, request, jsonify
import httpx
import asyncio
import logging
from dataclasses import dataclass
from quart_schema import QuartSchema, validate_request, validate_querystring
from common.config.config import ENTITY_VERSION
from common.repository.cyoda.cyoda_init import init_cyoda
from app_init.app_init import entity_service, cyoda_token

app = Quart(__name__)
QuartSchema(app)  # Initialize QuartSchema for future use

# Set up logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)

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
        response = await client.get("https://test-api.k6.io/public/crocodiles/")
        response.raise_for_status()  # Raise an error for bad responses
        return response.json()

@app.route('/api/crocodiles/ingest', methods=['POST'])
@validate_request(CrocodileIngest)  # Validation for POST request
async def ingest_crocodile_data(data: CrocodileIngest):
    try:
        # Fetch data from external API
        ingested_data = await fetch_crocodile_data()
        total_records = len(ingested_data)

        # Store data using entity_service
        for crocodile in ingested_data:
            await entity_service.add_item(
                token=cyoda_token,
                entity_model="crocodile",
                entity_version=ENTITY_VERSION,
                entity=crocodile
            )

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

    # Build condition for filtering
    condition = {}
    if name:
        condition['name'] = name
    if sex:
        condition['sex'] = sex
    if min_age is not None:
        condition['min_age'] = min_age
    if max_age is not None:
        condition['max_age'] = max_age

    try:
        # Fetch filtered crocodile data from entity_service
        crocodiles = await entity_service.get_items_by_condition(
            token=cyoda_token,
            entity_model="crocodile",
            entity_version=ENTITY_VERSION,
            condition=condition
        )
        return jsonify({"crocodiles": crocodiles}), 200
    except Exception as e:
        logger.exception("Error retrieving crocodiles")
        return jsonify({"error": "Failed to retrieve crocodiles"}), 500

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
```