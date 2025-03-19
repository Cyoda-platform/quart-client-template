import asyncio
import datetime
import logging

import httpx
from quart import Quart, request, jsonify
from quart_schema import QuartSchema

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)  # Enable QuartSchema

# In-memory persistence (acting as our local cache/database)
DATABASE = []


async def fetch_crocodile_data(source_url: str):
    async with httpx.AsyncClient() as client:
        response = await client.get(source_url)
        response.raise_for_status()  # Raises an exception for HTTP errors
        data = response.json()
        return data


async def process_crocodiles(data):
    # TODO: Add any processing logic if required.
    # This function simulates processing the data before persisting.
    global DATABASE
    # For the prototype, we simply assign the data to our in-memory store.
    DATABASE = data
    logger.info("Crocodile data ingested into the local cache.")
    return


@app.route('/api/crocodiles/ingest', methods=['POST'])
async def ingest_crocodiles():
    try:
        payload = await request.get_json()
        source = payload.get("source", "https://test-api.k6.io/public/crocodiles/")
        data = await fetch_crocodile_data(source)
        requested_at = datetime.datetime.utcnow().isoformat()
        job_id = "job-" + str(datetime.datetime.utcnow().timestamp())
        entity_job = {job_id: {"status": "processing", "requestedAt": requested_at}}
        logger.info("Starting ingestion job %s", job_id)
        # Fire and forget the processing task.
        asyncio.create_task(process_crocodiles(data))
        return jsonify({
            "status": "success",
            "message": "Data ingestion started",
            "job_id": job_id
        })
    except Exception as e:
        logger.exception(e)
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/api/crocodiles/', methods=['GET'])
async def get_crocodiles():
    try:
        # Retrieve filter parameters from query strings
        name_filter = request.args.get("name")
        sex_filter = request.args.get("sex")
        min_age = request.args.get("min_age", type=int)
        max_age = request.args.get("max_age", type=int)

        results = DATABASE

        if name_filter:
            results = [c for c in results if c.get("name") == name_filter]
        if sex_filter:
            results = [c for c in results if c.get("sex") == sex_filter]
        if min_age is not None:
            results = [c for c in results if c.get("age", 0) >= min_age]
        if max_age is not None:
            results = [c for c in results if c.get("age", 0) <= max_age]

        return jsonify({"status": "success", "data": results})
    except Exception as e:
        logger.exception(e)
        return jsonify({"status": "error", "message": str(e)}), 500


if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)