Absolutely, moving business and async logic into the workflow functions is a cleaner, more maintainable approach. It decouples controller endpoints from heavy logic, keeps API handlers thin, and leverages the new workflow capabilities fully.

---

### What we'll do:

- The endpoint `/api/companies/search` will primarily accept and validate input, then call `entity_service.add_item` **with the workflow function only**.
- The workflow function `process_companysearchresult` will:
  - Perform the PRH company search API call,
  - Filter active companies,
  - Query LEI info for each,
  - Compose results,
  - Update the entity state (including `status`, `results`, timestamps),
  - Save supplementary entities if needed (like raw data or logs) under different `entity_model`s,
  - Handle errors by setting entity error state.

- The `/api/companies/results/<search_id>` endpoint remains a simple retrieval.

- We'll **not** call `entity_service.add/update/delete` on the current entity inside the workflow to avoid recursion (only modify the entity dict directly).

---

### Updated complete code with logic moved into the workflow function

```python
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

# Remove in-memory cache; all state is stored in entities now

PRH_API_BASE = "https://avoindata.prh.fi/opendata-ytj-api/v3"
LEI_API_BASE = "https://api.gleif.org/api/v1/lei-records"  # Official LEI data source (GLEIF)

async def query_prh_companies(client: httpx.AsyncClient, company_name: str, max_results: int) -> list:
    params = {"name": company_name, "page": 1}
    companies = []
    while len(companies) < max_results:
        r = await client.get(f"{PRH_API_BASE}/companies", params=params)
        r.raise_for_status()
        data = r.json()
        page_results = data.get("results", []) or data.get("companies", [])
        if not page_results:
            break
        companies.extend(page_results)
        if "totalResults" in data and len(companies) >= data["totalResults"]:
            break
        params["page"] += 1
        if params["page"] > 5:  # Safety limit
            break
    return companies[:max_results]

def filter_active_companies(companies: list) -> list:
    return [c for c in companies if c.get("status") == 2]

async def query_lei(client: httpx.AsyncClient, business_id: str) -> Optional[str]:
    try:
        params = {"filter[entity.legalName]": business_id}
        r = await client.get(LEI_API_BASE, params=params)
        r.raise_for_status()
        data = r.json()
        records = data.get("data", [])
        if records:
            return records[0].get("id")
    except Exception:
        logger.exception(f"Failed to query LEI for businessId {business_id}")
    return None

def extract_company_data(company: dict, lei: Optional[str]) -> dict:
    return {
        "companyName": company.get("name"),
        "businessId": company.get("businessId"),
        "companyType": company.get("companyForm"),
        "registrationDate": company.get("registrationDate"),
        "status": "Active" if company.get("status") == 2 else "Inactive",
        "LEI": lei or "Not Available",
    }

# Workflow function: processes the entity asynchronously before persistence
async def process_companysearchresult(entity: dict) -> dict:
    """
    This function will perform the entire async enrichment workflow:
    - Call PRH API for companies,
    - Filter active,
    - Query LEI for each,
    - Compose results,
    - Update entity state (status, results, timestamps),
    - Handle errors gracefully.
    """
    company_name = entity.get("companyName")
    max_results = entity.get("maxResults", 50)
    if not company_name:
        entity["status"] = "failed"
        entity["error"] = "Missing 'companyName' in entity"
        return entity

    entity["status"] = "processing"
    entity["requestedAt"] = datetime.utcnow().isoformat()
    entity["results"] = None
    entity["completedAt"] = None
    entity["error"] = None

    async with httpx.AsyncClient(timeout=30) as client:
        try:
            companies = await query_prh_companies(client, company_name, max_results)
            active_companies = filter_active_companies(companies)

            results = []
            # Query LEI concurrently but limit concurrency to avoid overload
            semaphore = asyncio.Semaphore(5)

            async def get_lei_safe(comp):
                async with semaphore:
                    lei = await query_lei(client, comp.get("businessId", ""))
                    return extract_company_data(comp, lei)

            tasks = [get_lei_safe(comp) for comp in active_companies]
            results = await asyncio.gather(*tasks)

            entity["status"] = "completed"
            entity["results"] = results
            entity["completedAt"] = datetime.utcnow().isoformat()

            # Optionally, add supplementary raw data entity (different model)
            # E.g. raw PRH response saved as entity "companysearchraw"
            # await entity_service.add_item(...) <- NOT allowed on current entity_model, but allowed on different models
            # We'll just demonstrate how to do it without recursion:

            # Example:
            # await entity_service.add_item(
            #     token=cyoda_auth_service,
            #     entity_model="companysearchraw",
            #     entity_version=ENTITY_VERSION,
            #     entity={"searchId": entity.get("searchId"), "rawCompanies": companies},
            # )

        except Exception as e:
            entity["status"] = "failed"
            entity["error"] = str(e)
            logger.exception(f"Error processing company search for '{company_name}': {e}")

    return entity


@app.route("/api/companies/search", methods=["POST"])
@validate_request(CompanySearchRequest)
async def companies_search(data: CompanySearchRequest):
    """
    Thin controller: just add the entity with workflow function.
    Workflow handles the entire enrichment asynchronously before persistence.
    """
    try:
        # Compose entity to persist
        entity = {
            "companyName": data.companyName,
            "maxResults": data.maxResults or 50,
            # Initial status will be set by workflow
        }
        entity_id = await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model="companysearchresult",
            entity_version=ENTITY_VERSION,
            entity=entity,
            workflow=process_companysearchresult
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
    """
    Retrieve the search results entity by technical_id == search_id.
    Return status and results or errors.
    Support CSV output if Accept header requests it.
    """
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
```

---

### Key points:

- **The endpoint is minimal:** it just passes the validated data as an entity and triggers the workflow.
- **The workflow function `process_companysearchresult` is the full async enrichment pipeline.**
- **Entity state is updated in-place on `entity` dict inside the workflow.**
- **No infinite recursion risk** because entity_service calls are only on different models (commented example for supplementary raw data).
- **Error handling sets `status` and `error` fields on entity.**
- **Retrieval endpoint reads the persisted entity and returns appropriate status/errors.**

---

This design fully uses the new workflow function mechanism, keeps controllers clean, and centralizes async logic and side effects in workflow functions.

If you want, I can also help with adding supplementary entities or logging enhancements inside the workflow!

Would you like me to add those?