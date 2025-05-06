from dataclasses import dataclass
from typing import Optional

import asyncio
import csv
import io
import logging
from datetime import datetime
from typing import Dict, List

import httpx
from quart import Quart, jsonify, request, Response
from quart_schema import QuartSchema, validate_request

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# Input dataclass for POST /api/companies/search
@dataclass
class CompanySearchRequest:
    companyName: str
    maxResults: Optional[int] = 50

# In-memory storage for search results: searchId -> data
entity_job: Dict[str, Dict] = {}

PRH_API_BASE = "https://avoindata.prh.fi/opendata-ytj-api/v3"
LEI_API_BASE = "https://api.gleif.org/api/v1/lei-records"  # Official LEI data source (GLEIF)

# Helper to generate unique searchId
def generate_search_id() -> str:
    return datetime.utcnow().strftime("%Y%m%d%H%M%S%f")

# Query PRH API companies endpoint by companyName
async def query_prh_companies(client: httpx.AsyncClient, company_name: str, max_results: int) -> List[dict]:
    params = {"name": company_name, "page": 1}
    companies = []
    while len(companies) < max_results:
        r = await client.get(f"{PRH_API_BASE}/companies", params=params)
        r.raise_for_status()
        data = r.json()
        page_results = data.get("results") or data.get("companies") or []
        if not page_results:
            break
        companies.extend(page_results)
        # PRH API pagination: we assume 100 per page max, increase page if more needed
        if "totalResults" in data and len(companies) >= data["totalResults"]:
            break
        params["page"] += 1
        if params["page"] > 5:  # safety limit to avoid too many pages
            break
    return companies[:max_results]

# Filter active companies from PRH results
# Updated to use 'status' field int == 2 to indicate active (per user request)
def filter_active_companies(companies: List[dict]) -> List[dict]:
    active_companies = []
    for comp in companies:
        status = comp.get("status")
        if status == "2":  # 2 indicates active
            active_companies.append(comp)
    return active_companies

# Query GLEIF API for LEI by Business ID
async def query_lei(client: httpx.AsyncClient, business_id: str) -> Optional[str]:
    # TODO: Clarify exact mapping from Finnish Business ID to LEI or find a direct API
    params = {"filter[entity.legalName]": business_id}
    try:
        r = await client.get(LEI_API_BASE, params=params)
        r.raise_for_status()
        data = r.json()
        records = data.get("data", [])
        if records:
            return records[0].get("id")
    except Exception as e:
        logger.exception(f"Failed to query LEI for business ID {business_id}: {e}")
    return None

# Extract required fields from PRH company data
def extract_company_data(company: dict, lei: Optional[str]) -> dict:
    return {
        "companyName": company.get("name"),
        "businessId": company.get("businessId"),
        "companyType": company.get("companyForm"),
        "registrationDate": company.get("registrationDate"),
        # Use 'status' int field and convert 2 to 'Active' else 'Inactive'
        "status": "Active" if company.get("status") == 2 else "Inactive",
        "LEI": lei or "Not Available",
    }

# Background processing of the search + enrichment
async def process_entity(entity_job: Dict[str, Dict], search_id: str, company_name: str, max_results: int):
    async with httpx.AsyncClient(timeout=30) as client:
        try:
            companies = await query_prh_companies(client, company_name, max_results)
            active_companies = filter_active_companies(companies)
            results = []
            for comp in active_companies:
                lei = await query_lei(client, comp.get("businessId", ""))
                data = extract_company_data(comp, lei)
                results.append(data)
            entity_job[search_id]["status"] = "completed"
            entity_job[search_id]["results"] = results
            entity_job[search_id]["completedAt"] = datetime.utcnow().isoformat()
            logger.info(f"Completed processing searchId={search_id} with {len(results)} results")
        except Exception as e:
            entity_job[search_id]["status"] = "failed"
            entity_job[search_id]["error"] = str(e)
            logger.exception(f"Error processing searchId={search_id}: {e}")

@app.route("/api/companies/search", methods=["POST"])
@validate_request(CompanySearchRequest)  # Validation last for POST (workaround for quart-schema issue)
async def companies_search(data: CompanySearchRequest):
    try:
        company_name = data.companyName
        max_results = data.maxResults or 50
        search_id = generate_search_id()
        entity_job[search_id] = {
            "status": "processing",
            "requestedAt": datetime.utcnow().isoformat(),
            "results": None,
        }
        asyncio.create_task(process_entity(entity_job, search_id, company_name, max_results))
        return jsonify({
            "searchId": search_id,
            "totalCompanies": None,
            "message": "Search started and enrichment is processing in background"
        })
    except Exception as e:
        logger.exception(f"Error in /api/companies/search: {e}")
        return jsonify({"error": "Internal server error"}), 500

@app.route("/api/companies/results/<string:search_id>", methods=["GET"])
async def companies_results(search_id):
    job = entity_job.get(search_id)
    if not job:
        return jsonify({"error": "searchId not found"}), 404
    status = job.get("status")
    if status == "processing":
        return jsonify({"searchId": search_id, "status": "processing", "message": "Results not ready yet"}), 202
    if status == "failed":
        return jsonify({"searchId": search_id, "status": "failed", "error": job.get("error")}), 500
    results = job.get("results", [])

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
        return jsonify({"searchId": search_id, "results": results})

if __name__ == '__main__':
    import logging
    logging.basicConfig(level=logging.INFO)
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
