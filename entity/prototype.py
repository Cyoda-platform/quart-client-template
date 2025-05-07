```python
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema

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


async def fetch_api_data(client: httpx.AsyncClient, endpoint: str) -> Any:
    url = f"{API_BASE}{endpoint}"
    try:
        resp = await client.get(url, timeout=HTTP_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        # The API returns a structure with `response` key holding data in most cases
        return data.get("response", data)
    except Exception as e:
        logger.exception(f"Failed to fetch data from {url}: {e}")
        return None


async def process_entity(job_id: str):
    """Main processing: fetch, transform, aggregate, generate report, send email."""
    try:
        logger.info(f"Job {job_id}: Starting data ingestion and processing")
        async with httpx.AsyncClient() as client:
            # Fetch data from endpoints
            products = await fetch_api_data(client, API_ENDPOINTS["products"])
            categories = await fetch_api_data(client, API_ENDPOINTS["categories"])
            orders = await fetch_api_data(client, API_ENDPOINTS["orders"])

            # TODO: If orders endpoint is not available or requires auth, replace with empty or mock data
            if orders is None:
                orders = []
                logger.info("Orders data unavailable, using empty list")

            # Data Transformation (simple cleaning example)
            # TODO: Implement additional cleaning if needed (e.g., normalize fields, remove duplicates)
            products_clean = products if isinstance(products, list) else []
            categories_clean = categories if isinstance(categories, list) else []
            orders_clean = orders if isinstance(orders, list) else []

            # Aggregation examples:
            # 1) Total sales (sum order totals)
            total_sales = 0.0
            for order in orders_clean:
                # Assuming order has 'total_price' or similar key, fallback to 0
                price = order.get("total_price") or order.get("totalPrice") or 0
                try:
                    total_sales += float(price)
                except Exception:
                    pass

            # 2) Category-wise product count
            category_counts = {}
            # Assuming products have category id or name field
            for product in products_clean:
                cat_name = product.get("category") or product.get("category_name") or "Unknown"
                category_counts[cat_name] = category_counts.get(cat_name, 0) + 1

            # Generate report (summary & details)
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

            # Save to in-memory cache
            global latest_report_summary, latest_report_details
            latest_report_summary = summary
            latest_report_details = details

            # Simulate sending email
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


@app.route("/api/ingest-process", methods=["POST"])
async def ingest_process():
    data = await request.get_json(force=True)
    trigger_source = data.get("triggerSource", "manual")
    job_id = datetime.utcnow().strftime("%Y%m%d%H%M%S%f")

    entity_job[job_id] = {
        "status": "processing",
        "requestedAt": datetime.utcnow().isoformat(),
        "triggerSource": trigger_source
    }

    # Fire and forget processing
    asyncio.create_task(process_entity(job_id))

    return jsonify({
        "status": "started",
        "message": "Data ingestion and processing initiated",
        "jobId": job_id
    }), 202


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


@app.route("/api/admin/email", methods=["POST"])
async def update_admin_email():
    data = await request.get_json(force=True)
    email = data.get("email")
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
```