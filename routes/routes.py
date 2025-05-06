from dataclasses import dataclass
from typing import Optional

import asyncio
import csv
import io
import logging
from datetime import datetime

import httpx
from quart import Quart, jsonify, request, Response
from quart_schema import QuartSchema, validate_request

from app_init.app_init import BeanFactory
from common.config.config import ENTITY_VERSION

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

factory = BeanFactory(config={'CHAT_REPOSITORY': 'cyoda'})
entity_service = factory.get_services()['entity_service']
cyoda_auth_service = factory.get_services()["cyoda_auth_service"]

app = Quart(__name__)
QuartSchema(app)

@dataclass
class CompanySearchRequest:
    companyName: str
    maxResults: Optional[int] = 50

PRH_API_BASE = "https://avoindata.prh.fi/opendata-ytj-api/v3"
LEI_API_BASE = "https://api.gleif.org/api/v1/lei-records"  # Official LEI data source (GLEIF)


@app.route("/api/companies/search", methods=["POST"])
@validate_request(CompanySearchRequest)
async def companies_search(data: CompanySearchRequest):
    try:
        entity = {
            "companyName": data.companyName,
            "maxResults": data.maxResults or 50,
        }
        entity_id = await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model="companysearchresult",
            entity_version=ENTITY_VERSION,
            entity=entity,
            )
        return jsonify({
            "searchId": entity_id,
            "message": "Search started and enrichment is processing asynchronously"
        })
    except Exception as e:
        logger.exception(f"Error in /api/companies/search endpoint: {e}")
        return jsonify({"error": "Internal server error"}), 500


@app.route("/api/companies/results/<string:search_id>", methods=["GET"])
async def companies_results(search_id):
    try:
        entity = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model="companysearchresult",
            entity_version=ENTITY_VERSION,
            technical_id=search_id,
        )
        if not entity:
            return jsonify({"error": "searchId not found"}), 404

        status = entity.get("status", "processing")
        if status == "processing":
            return jsonify({"searchId": search_id, "status": "processing", "message": "Results not ready yet"}), 202
        if status == "failed":
            return jsonify({"searchId": search_id, "status": "failed", "error": entity.get("error")}), 500

        results = entity.get("results", [])
        completed_at = entity.get("completedAt")

        accept = request.headers.get("Accept", "application/json")
        if "text/csv" in accept:
            output = io.StringIO()
            writer = csv.DictWriter(output, fieldnames=[
                "companyName", "businessId", "companyType", "registrationDate", "status", "LEI"
            ])
            writer.writeheader()
            for row in results:
                writer.writerow(row)
            return Response(output.getvalue(), mimetype="text/csv")
        else:
            return jsonify({"searchId": search_id, "results": results, "completedAt": completed_at})

    except Exception as e:
        logger.exception(f"Error retrieving results for searchId={search_id}: {e}")
        return jsonify({"error": "Internal server error"}), 500


if __name__ == '__main__':
    import logging
    logging.basicConfig(level=logging.INFO)
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)