from dataclasses import dataclass
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# In-memory cache for prototype persistence
entity_job: Dict[str, Dict[str, Any]] = {}
latest_report_summary: Dict[str, Any] = {}
latest_report_details: Dict[str, Any] = {}
admin_email_config: Dict[str, str] = {"email": None}

# Automation Exercise API base URL
API_BASE = "https://automationexercise.com/api"

# Endpoints from the API list (limited to product list, categories, orders)
API_ENDPOINTS = {
    "products": "/productsList",
    "categories": "/getCategoriesList",
    "orders": "/ordersList"  # TODO: Confirm if ordersList endpoint exists and if auth required
}

# HTTP client timeout
HTTP_TIMEOUT = 20

@dataclass
class IngestProcessRequest:
    triggerSource: str  # manual or scheduler

@dataclass
class AdminEmailRequest:
    email: str


async def fetch_api_data(client: httpx.AsyncClient, endpoint: str) -> Any:
    url = f"{API_BASE}{endpoint}"
    try:
        resp = await client.get(url, timeout=HTTP_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        return data.get("response", data)
    except Exception as e:
        logger.exception(f"Failed to fetch data from {url}: {e}")
        return None


async def process_entity(job_id: str):
    try:
        logger.info(f"Job {job_id}: Starting data ingestion and processing")
        async with httpx.AsyncClient() as client:
            products = await fetch_api_data(client, API_ENDPOINTS["products"])
            categories = await fetch_api_data(client, API_ENDPOINTS["categories"])
            orders = await fetch_api_data(client, API_ENDPOINTS["orders"])

            if orders is None:
                orders = []
                logger.info("Orders data unavailable, using empty list")

            products_clean = products if isinstance(products, list) else []
            categories_clean = categories if isinstance(categories, list) else []
            orders_clean = orders if isinstance(orders, list) else []

            total_sales = 0.0
            for order in orders_clean:
                price = order.get("total_price") or order.get("totalPrice") or 0
                try:
                    total_sales += float(price)
                except Exception:
                    pass

            category_counts = {}
            for product in products_clean:
                cat_name = product.get("category") or product.get("category_name") or "Unknown"
                category_counts[cat_name] = category_counts.get(cat_name, 0) + 1

            report_date = datetime.utcnow().strftime("%Y-%m-%d")

            summary = {
                "reportDate": report_date,
                "totalSales": round(total_sales, 2),
                "categoryWiseProducts": category_counts,
            }

            details = {
                "reportDate": report_date,
                "products": products_clean,
                "categories": categories_clean,
                "aggregations": {
                    "totalSales": round(total_sales, 2),
                    "categoryWiseProducts": category_counts,
                },
            }

            global latest_report_summary, latest_report_details
            latest_report_summary = summary
            latest_report_details = details

            await send_report_email(admin_email_config.get("email"), summary)

            entity_job[job_id]["status"] = "completed"
            logger.info(f"Job {job_id}: Processing completed")

    except Exception as e:
        entity_job[job_id]["status"] = "failed"
        logger.exception(f"Job {job_id}: Processing failed with exception: {e}")


async def send_report_email(email: str, report_summary: Dict[str, Any]):
    if not email:
        logger.warning("Admin email not configured; skipping email sending")
        return
    # TODO: Replace with actual email sending logic or integration with email service
    logger.info(f"Sending report to {email}:\n{report_summary}")

# POST validation must go LAST (due to quart-schema issue)
@app.route("/api/ingest-process", methods=["POST"])
@validate_request(IngestProcessRequest)
async def ingest_process(data: IngestProcessRequest):
    trigger_source = data.triggerSource
    job_id = datetime.utcnow().strftime("%Y%m%d%H%M%S%f")

    entity_job[job_id] = {
        "status": "processing",
        "requestedAt": datetime.utcnow().isoformat(),
        "triggerSource": trigger_source
    }

    asyncio.create_task(process_entity(job_id))

    return jsonify({
        "status": "started",
        "message": "Data ingestion and processing initiated",
        "jobId": job_id
    }), 202

# GET requests validation must go FIRST (workaround for quart-schema issue)
@app.route("/api/report/summary", methods=["GET"])
async def report_summary():
    if not latest_report_summary:
        return jsonify({"message": "No report available"}), 404
    return jsonify(latest_report_summary)

@app.route("/api/report/details", methods=["GET"])
async def report_details():
    if not latest_report_details:
        return jsonify({"message": "No report available"}), 404
    return jsonify(latest_report_details)

# POST validation must go LAST (due to quart-schema issue)
@app.route("/api/admin/email", methods=["POST"])
@validate_request(AdminEmailRequest)
async def update_admin_email(data: AdminEmailRequest):
    email = data.email
    if not email:
        return jsonify({"status": "error", "message": "Email is required"}), 400
    admin_email_config["email"] = email
    logger.info(f"Admin email updated to {email}")
    return jsonify({"status": "success", "message": "Admin email updated"})

if __name__ == '__main__':
    import sys
    import logging.config

    logging.basicConfig(
        stream=sys.stdout,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=logging.INFO,
    )

    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
