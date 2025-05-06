import asyncio
import logging
from datetime import datetime
from typing import Optional

import httpx

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

PRH_API_BASE = "https://avoindata.prh.fi/opendata-ytj-api/v3"
LEI_API_BASE = "https://api.gleif.org/api/v1/lei-records"  # Official LEI data source (GLEIF)

async def process_query_prh_companies(entity: dict):
    company_name = entity.get("companyName")
    max_results = entity.get("maxResults", 50)
    params = {"name": company_name, "page": 1}
    companies = []
    try:
        async with httpx.AsyncClient(timeout=30) as client:
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
                if params["page"] > 5:
                    break
    except Exception as e:
        logger.exception(f"Error querying PRH companies for '{company_name}': {e}")
        raise
    entity["companies"] = companies[:max_results]

def process_filter_active_companies(entity: dict):
    companies = entity.get("companies", [])
    entity["active_companies"] = [c for c in companies if c.get("status") == 2]

async def process_query_lei(entity: dict):
    active_companies = entity.get("active_companies", [])
    results = []
    semaphore = asyncio.Semaphore(5)
    async with httpx.AsyncClient(timeout=30) as client:
        async def get_lei_safe(comp):
            async with semaphore:
                lei = None
                business_id = comp.get("businessId", "")
                if business_id:
                    try:
                        params = {"filter[entity.legalName]": business_id}
                        r = await client.get(LEI_API_BASE, params=params)
                        r.raise_for_status()
                        data = r.json()
                        records = data.get("data", [])
                        if records:
                            lei = records[0].get("id")
                    except Exception:
                        logger.exception(f"Failed to query LEI for businessId {business_id}")
                return process_extract_company_data(comp, lei)
        tasks = [get_lei_safe(comp) for comp in active_companies]
        results = await asyncio.gather(*tasks)
    entity["results"] = results

def process_extract_company_data(company: dict, lei: Optional[str]) -> dict:
    return {
        "companyName": company.get("name"),
        "businessId": company.get("businessId"),
        "companyType": company.get("companyForm"),
        "registrationDate": company.get("registrationDate"),
        "status": "Active" if company.get("status") == 2 else "Inactive",
        "LEI": lei or "Not Available",
    }