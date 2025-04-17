```python
import asyncio
import logging
from dataclasses import dataclass
from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request, validate_querystring
import httpx

# Setup logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Initialize the Quart application
app = Quart(__name__)
QuartSchema(app)

# In-memory cache for crocodile data
crocodile_cache = {}

@dataclass
class IngestRequest:
    api_url: str

@dataclass
class FilterQuery:
    name: str = None
    sex: str = None
    age_min: int = None
    age_max: int = None

@app.route('/api/crocodiles/ingest', methods=['POST'])
@validate_request(IngestRequest)  # Validation should be last for POST requests
async def ingest_crocodile_data(data: IngestRequest):
    api_url = data.api_url

    if not api_url:
        return jsonify({"message": "API URL is required"}), 400

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(api_url)
            response.raise_for_status()  # Raise an error for bad responses
            crocodiles = response.json()

            # Cache the crocodile data
            for croc in crocodiles:
                crocodile_cache[croc['id']] = {
                    "name": croc['name'],
                    "sex": croc['sex'],
                    "date_of_birth": croc['date_of_birth'],
                    "age": croc['age']
                }

            return jsonify({"message": "Data ingested successfully", "count": len(crocodiles)}), 200

    except Exception as e:
        logger.exception(e)
        return jsonify({"message": "Error ingesting data"}), 500

@app.route('/api/crocodiles', methods=['GET'])
@validate_querystring(FilterQuery)  # Validation should be first for GET requests
async def get_crocodile_data():
    name = request.args.get('name')
    sex = request.args.get('sex')
    age_min = request.args.get('age_min', type=int)
    age_max = request.args.get('age_max', type=int)

    filtered_crocodiles = []

    for croc in crocodile_cache.values():
        if name and name.lower() not in croc['name'].lower():
            continue
        if sex and croc['sex'] != sex:
            continue
        if age_min is not None and croc['age'] < age_min:
            continue
        if age_max is not None and croc['age'] > age_max:
            continue
        filtered_crocodiles.append(croc)

    return jsonify({"crocodiles": filtered_crocodiles}), 200

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
```