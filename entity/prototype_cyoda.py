import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any

import httpx
from quart import Quart, jsonify, render_template_string, request
from quart_schema import QuartSchema, validate_request, validate_querystring

from app_init.app_init import BeanFactory
from common.config.config import ENTITY_VERSION

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

factory = BeanFactory(config={'CHAT_REPOSITORY': 'cyoda'})
entity_service = factory.get_services()['entity_service']
cyoda_auth_service = factory.get_services()["cyoda_auth_service"]

app = Quart(__name__)
QuartSchema(app)

# Workaround for quart-schema defect:
# - For GET requests, put validation decorator first
# - For POST requests, put validation decorator last

@dataclass
class FetchAnalyzeRequest:
    # No fields required currently; placeholder for future request params
    pass

# Instead of local cache for prototype jobs, store jobs in entity_service
# We'll use entity name "prototype" (underscore lowercase)
entity_name = "prototype"

SAUCEDEMO_LOGIN_URL = "https://www.saucedemo.com/"
SAUCEDEMO_INVENTORY_URL = "https://www.saucedemo.com/inventory.html"
USERNAME = "standard_user"
PASSWORD = "secret_sauce"


async def login_and_get_inventory(client: httpx.AsyncClient) -> str:
    try:
        r1 = await client.get(SAUCEDEMO_LOGIN_URL)
        r1.raise_for_status()

        # Correct form field names for SauceDemo login: "user-name", "password"
        # Also set headers for form submission
        login_data = {"user-name": USERNAME, "password": PASSWORD}
        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        r2 = await client.post(SAUCEDEMO_LOGIN_URL, data=login_data, headers=headers, follow_redirects=True)
        r2.raise_for_status()

        r3 = await client.get(SAUCEDEMO_INVENTORY_URL)
        r3.raise_for_status()

        return r3.text
    except Exception as e:
        logger.exception("Failed to login and retrieve inventory page")
        raise e


def parse_inventory(html: str) -> list:
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    inventory_items = []
    items = soup.select(".inventory_item")
    for item in items:
        name_el = item.select_one(".inventory_item_name")
        desc_el = item.select_one(".inventory_item_desc")
        price_el = item.select_one(".inventory_item_price")
        if not (name_el and desc_el and price_el):
            continue
        name = name_el.text.strip()
        description = desc_el.text.strip()
        try:
            price = float(price_el.text.strip().replace("$", ""))
        except Exception:
            price = 0.0
        inventory = 1  # TODO: adjust when real stock quantity is available
        inventory_items.append({"name": name, "description": description, "price": price, "inventory": inventory})
    return inventory_items


def analyze_products(products: list) -> dict:
    if not products:
        return {}
    total_products = len(products)
    total_price = sum(p["price"] for p in products)
    average_price = total_price / total_products
    highest = max(products, key=lambda p: p["price"])
    lowest = min(products, key=lambda p: p["price"])
    total_inventory_value = sum(p["price"] * p["inventory"] for p in products)
    return {
        "total_products": total_products,
        "average_price": round(average_price, 2),
        "highest_priced_item": {"name": highest["name"], "price": highest["price"]},
        "lowest_priced_item": {"name": lowest["name"], "price": lowest["price"]},
        "total_inventory_value": round(total_inventory_value, 2),
    }


async def process_entity(job_id: str):
    try:
        logger.info(f"Job {job_id}: Starting data fetch and analysis")
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            html = await login_and_get_inventory(client)
        products = parse_inventory(html)
        summary = analyze_products(products)

        # update the job item in entity_service
        # get current job data
        job_data = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model=entity_name,
            entity_version=ENTITY_VERSION,
            technical_id=job_id
        )
        if job_data is None:
            logger.error(f"Job {job_id}: Not found during process_entity update")
            return

        job_data["status"] = "completed"
        job_data["completedAt"] = datetime.utcnow().isoformat()
        job_data["summary"] = summary

        await entity_service.update_item(
            token=cyoda_auth_service,
            entity_model=entity_name,
            entity_version=ENTITY_VERSION,
            entity=job_data,
            technical_id=job_id,
            meta={}
        )
        logger.info(f"Job {job_id}: Completed successfully")
    except Exception as e:
        logger.exception(f"Job {job_id}: Failed with error")
        try:
            job_data = await entity_service.get_item(
                token=cyoda_auth_service,
                entity_model=entity_name,
                entity_version=ENTITY_VERSION,
                technical_id=job_id
            )
            if job_data is not None:
                job_data["status"] = "failed"
                job_data["error"] = str(e)
                await entity_service.update_item(
                    token=cyoda_auth_service,
                    entity_model=entity_name,
                    entity_version=ENTITY_VERSION,
                    entity=job_data,
                    technical_id=job_id,
                    meta={}
                )
        except Exception as e2:
            logger.exception(f"Job {job_id}: Failed to update failure status: {e2}")


@app.route("/api/fetch-and-analyze", methods=["POST"])
@validate_request(FetchAnalyzeRequest)  # validation last for POST (workaround)
async def fetch_and_analyze(data: FetchAnalyzeRequest):
    requested_at = datetime.utcnow().isoformat()
    job_id = requested_at.replace(":", "-").replace(".", "-")
    job_obj = {"status": "processing", "requestedAt": requested_at}
    try:
        # add job to entity_service
        new_id = await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model=entity_name,
            entity_version=ENTITY_VERSION,
            entity=job_obj
        )
        # new_id is string, use it as job_id
        asyncio.create_task(process_entity(new_id))
        return jsonify({"job_id": new_id, "status": "processing", "message": "Data fetch and analysis started"})
    except Exception as e:
        logger.exception("Failed to create new job")
        return jsonify({"error": "Failed to start job"}), 500


@app.route("/api/report", methods=["GET"])
async def get_report():
    try:
        # Retrieve latest completed job's summary by condition
        condition = {
            "cyoda": {
                "type": "group",
                "operator": "AND",
                "conditions": [
                    {
                        "jsonPath": "$.status",
                        "operatorType": "EQUALS",
                        "value": "completed",
                        "type": "simple"
                    }
                ]
            }
        }
        completed_jobs = await entity_service.get_items_by_condition(
            token=cyoda_auth_service,
            entity_model=entity_name,
            entity_version=ENTITY_VERSION,
            condition=condition
        )
        if not completed_jobs:
            # Return empty summary instead of 404 to avoid client error
            empty_summary = {
                "total_products": 0,
                "average_price": 0.0,
                "highest_priced_item": {"name": "", "price": 0.0},
                "lowest_priced_item": {"name": "", "price": 0.0},
                "total_inventory_value": 0.0
            }
            return jsonify(empty_summary)
        # Pick the latest completed job by completedAt datetime
        latest_job = max(
            completed_jobs,
            key=lambda j: j.get("completedAt", "")
        )
        summary = latest_job.get("summary", {})
        return jsonify(summary)
    except Exception as e:
        logger.exception("Failed to get report")
        return jsonify({"error": "Failed to get report"}), 500


HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8" />
    <title>SauceDemo Product Summary Report</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 2rem; }
        h1 { color: #333; }
        table { border-collapse: collapse; width: 50%; }
        th, td { border: 1px solid #ccc; padding: 8px 12px; text-align: left; }
        th { background-color: #f4f4f4; }
        .summary { margin-top: 1rem; }
        button { margin-top: 20px; padding: 8px 16px; }
    </style>
</head>
<body>
    <h1>SauceDemo Product Summary Report</h1>
    {% if summary %}
    <table>
        <tr><th>Total Products</th><td>{{ summary.total_products }}</td></tr>
        <tr><th>Average Price</th><td>${{ summary.average_price }}</td></tr>
        <tr><th>Highest Priced Item</th><td>{{ summary.highest_priced_item.name }} (${{ summary.highest_priced_item.price }})</td></tr>
        <tr><th>Lowest Priced Item</th><td>{{ summary.lowest_priced_item.name }} (${{ summary.lowest_priced_item.price }})</td></tr>
        <tr><th>Total Inventory Value</th><td>${{ summary.total_inventory_value }}</td></tr>
    </table>
    {% else %}
    <p>No summary available yet. Please trigger data fetch and analysis.</p>
    {% endif %}
    <form method="post" action="/api/fetch-and-analyze" id="refreshForm">
        <button type="submit">Refresh Data</button>
    </form>
    <script>
        const form = document.getElementById('refreshForm');
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            const resp = await fetch('/api/fetch-and-analyze', {method: 'POST'});
            if (resp.ok) {
                alert('Data fetch started. Please refresh the page after a few seconds.');
            } else {
                alert('Failed to start data fetch.');
            }
        });
    </script>
</body>
</html>
"""


@app.route("/", methods=["GET"])
async def index():
    try:
        # get latest completed summary
        condition = {
            "cyoda": {
                "type": "group",
                "operator": "AND",
                "conditions": [
                    {
                        "jsonPath": "$.status",
                        "operatorType": "EQUALS",
                        "value": "completed",
                        "type": "simple"
                    }
                ]
            }
        }
        completed_jobs = await entity_service.get_items_by_condition(
            token=cyoda_auth_service,
            entity_model=entity_name,
            entity_version=ENTITY_VERSION,
            condition=condition
        )
        summary = None
        if completed_jobs:
            latest_job = max(
                completed_jobs,
                key=lambda j: j.get("completedAt", "")
            )
            summary = latest_job.get("summary", None)
        return await render_template_string(HTML_TEMPLATE, summary=summary)
    except Exception as e:
        logger.exception("Failed to render index page")
        return await render_template_string(HTML_TEMPLATE, summary=None)


if __name__ == "__main__":
    import sys
    logging.basicConfig(stream=sys.stdout, level=logging.INFO)
    app.run(use_reloader=False, debug=True, host="0.0.0.0", port=8000, threaded=True)