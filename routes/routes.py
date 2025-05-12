from dataclasses import dataclass
from typing import Optional, List, Dict, Any

import asyncio
import logging
from datetime import datetime

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request, validate_querystring

from app_init.app_init import BeanFactory
from common.config.config import ENTITY_VERSION

factory = BeanFactory(config={'CHAT_REPOSITORY': 'cyoda'})
entity_service = factory.get_services()['entity_service']
cyoda_auth_service = factory.get_services()["cyoda_auth_service"]

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

entity_job: Dict[str, Dict[str, Any]] = {}

THE_CAT_API_BASE = "https://api.thecatapi.com/v1"
CAT_FACTS_API_BASE = "https://catfact.ninja"
THE_CAT_API_HEADERS = {
    # "x-api-key": "YOUR_API_KEY"  # TODO: Add API key if needed
}

def generate_id(prefix: str, idx: int) -> str:
    return f"{prefix}_{idx}"

@dataclass
class FetchDataRequest:
    source: Optional[str] = "default"
    dataTypes: List[str] = None
    filters: Optional[Dict[str, Any]] = None

@dataclass
class AnalyzeDataRequest:
    analysisType: str
    parameters: Optional[Dict[str, Any]] = None

@dataclass
class CatsDataGetQuery:
    type: Optional[str] = None
    breed: Optional[str] = None
    limit: Optional[int] = None

async def process_fetch_data(job_id: str, params: FetchDataRequest):
    try:
        source = params.source or "default"
        data_types = params.dataTypes or []
        filters = params.filters or {}
        limit = filters.get("limit", 5) or 5
        limit = int(limit) if isinstance(limit, (int, str)) and str(limit).isdigit() else 5

        if "images" in data_types:
            for i in range(limit):
                entity = {"id": generate_id("img", i)}
                try:
                    await entity_service.add_item(
                        token=cyoda_auth_service,
                        entity_model="images",
                        entity_version=ENTITY_VERSION,
                        entity=entity,
                    )
                except Exception as e:
                    logger.exception(f"Failed to add image entity: {e}")

        if "breeds" in data_types:
            try:
                async with httpx.AsyncClient() as client:
                    resp = await client.get(f"{THE_CAT_API_BASE}/breeds", headers=THE_CAT_API_HEADERS, timeout=10)
                    resp.raise_for_status()
                    all_breeds = resp.json()
            except Exception as e:
                all_breeds = []
                logger.exception(f"Failed to fetch breeds for IDs: {e}")

            breed_filter = filters.get("breed")
            filtered_breeds = all_breeds
            if breed_filter:
                filtered_breeds = [b for b in all_breeds if breed_filter.lower() in b.get("name", "").lower()]

            for breed in filtered_breeds[:limit]:
                entity = {"id": breed.get("id")}
                if not entity["id"]:
                    continue
                try:
                    await entity_service.add_item(
                        token=cyoda_auth_service,
                        entity_model="breeds",
                        entity_version=ENTITY_VERSION,
                        entity=entity,
                    )
                except Exception as e:
                    logger.exception(f"Failed to add breed entity: {e}")

        if "facts" in data_types:
            for i in range(limit):
                entity = {"id": generate_id("fact", i)}
                try:
                    await entity_service.add_item(
                        token=cyoda_auth_service,
                        entity_model="facts",
                        entity_version=ENTITY_VERSION,
                        entity=entity,
                    )
                except Exception as e:
                    logger.exception(f"Failed to add fact entity: {e}")

        entity_job[job_id]["status"] = "completed"
        entity_job[job_id]["completedAt"] = datetime.utcnow().isoformat()
        count = 0
        for dt in data_types:
            try:
                items = await entity_service.get_items(
                    token=cyoda_auth_service,
                    entity_model=dt,
                    entity_version=ENTITY_VERSION,
                )
                count += len(items)
            except Exception as e:
                logger.exception(f"Failed to count items for {dt}: {e}")
        entity_job[job_id]["count"] = count

        logger.info(f"Job {job_id} completed, fetched data types: {data_types}")

    except Exception as e:
        entity_job[job_id]["status"] = "failed"
        logger.exception(f"Failed processing fetch data job {job_id}: {e}")

@app.route("/cats/data/fetch", methods=["POST"])
@validate_request(FetchDataRequest)
async def cats_data_fetch(data: FetchDataRequest):
    job_id = f"job_{datetime.utcnow().timestamp()}"
    requested_at = datetime.utcnow().isoformat()
    entity_job[job_id] = {"status": "processing", "requestedAt": requested_at}
    asyncio.create_task(process_fetch_data(job_id, data))
    return jsonify({"status": "processing", "jobId": job_id, "requestedAt": requested_at}), 202

@app.route("/cats/data", methods=["GET"])
@validate_querystring(CatsDataGetQuery)
async def cats_data_get():
    query_args = request.args
    data_type = query_args.get("type", None)
    breed_filter = query_args.get("breed", None)
    limit = query_args.get("limit", None)
    try:
        limit = int(limit) if limit else None
    except ValueError:
        limit = None

    supported_types = ["images", "breeds", "facts"]
    if data_type not in supported_types:
        return jsonify({"error": f"Unsupported data type '{data_type}'"}), 400

    try:
        data_items = await entity_service.get_items(
            token=cyoda_auth_service,
            entity_model=data_type,
            entity_version=ENTITY_VERSION
        )
    except Exception as e:
        logger.exception(f"Failed to get items for {data_type}: {e}")
        return jsonify({"error": "Failed to retrieve data"}), 500

    if data_type == "breeds" and breed_filter:
        data_items = [item for item in data_items if item.get("content") and breed_filter.lower() in item["content"].get("name", "").lower()]

    if limit:
        data_items = data_items[:limit]

    return jsonify({"dataType": data_type, "data": data_items})

@app.route("/cats/data/analyze", methods=["POST"])
@validate_request(AnalyzeDataRequest)
async def cats_data_analyze(data: AnalyzeDataRequest):
    analysis_type = data.analysisType
    parameters = data.parameters or {}

    try:
        images = await entity_service.get_items(
            token=cyoda_auth_service,
            entity_model="images",
            entity_version=ENTITY_VERSION
        )
        facts = await entity_service.get_items(
            token=cyoda_auth_service,
            entity_model="facts",
            entity_version=ENTITY_VERSION
        )
    except Exception as e:
        logger.exception(f"Failed to retrieve data for analysis: {e}")
        return jsonify({"error": "Failed to retrieve data for analysis"}), 500

    if analysis_type == "popularity":
        breed_name = parameters.get("breed")
        if breed_name:
            count_images = sum(1 for i in images if i.get("content") and breed_name.lower() in i["content"].lower())
            count_facts = sum(1 for f in facts if f.get("content") and breed_name.lower() in f["content"].lower())
            result = {"breed": breed_name, "popularityScore": count_images + count_facts}
        else:
            result = {"error": "breed parameter required for popularity analysis"}
        return jsonify({"analysisType": analysis_type, "result": result})

    elif analysis_type == "factFrequency":
        word_count = {}
        for fact_item in facts:
            content = fact_item.get("content")
            if not content:
                continue
            words = content.lower().split()
            for w in words:
                word_count[w] = word_count.get(w, 0) + 1
        top_words = sorted(word_count.items(), key=lambda x: x[1], reverse=True)[:10]
        result = {word: count for word, count in top_words}
        return jsonify({"analysisType": analysis_type, "result": result})

    else:
        return jsonify({"error": f"Unsupported analysis type '{analysis_type}'"}), 400

if __name__ == '__main__':
    import sys
    logging.basicConfig(stream=sys.stdout, level=logging.INFO,
                        format='%(asctime)s %(levelname)s %(name)s: %(message)s')
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
