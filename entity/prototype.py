```python
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any

import httpx
from quart import Quart, jsonify, render_template_string, request
from quart_schema import QuartSchema

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# In-memory local cache for prototype
entity_job: Dict[str, Dict[str, Any]] = {}

# Cached summary report (in a real app, persistence would be used)
latest_summary: Dict[str, Any] = {}

SAUCEDEMO_LOGIN_URL = "https://www.saucedemo.com/"
SAUCEDEMO_INVENTORY_URL = "https://www.saucedemo.com/inventory.html"

USERNAME = "standard_user"
PASSWORD = "secret_sauce"


async def login_and_get_inventory(client: httpx.AsyncClient) -> str:
    """
    Log into SauceDemo and return the inventory page HTML.
    """
    try:
        # Step 1: Get login page to retrieve cookies and any tokens (if needed)
        r1 = await client.get(SAUCEDEMO_LOGIN_URL)
        r1.raise_for_status()

        # Step 2: Post login form
        login_data = {
            "user-name": USERNAME,
            "password": PASSWORD,
        }
        # SauceDemo uses form POST to /login or / (same endpoint)
        r2 = await client.post(SAUCEDEMO_LOGIN_URL, data=login_data, follow_redirects=True)
        r2.raise_for_status()

        # After login, inventory page should be accessible
        r3 = await client.get(SAUCEDEMO_INVENTORY_URL)
        r3.raise_for_status()
        return r3.text
    except Exception as e:
        logger.exception("Failed to login and retrieve inventory page")
        raise e


def parse_inventory(html: str) -> list:
    """
    Parse the inventory page HTML to extract product items.
    Extract fields: item name, description, price, and inventory (stock quantity).
    Inventory page does not explicitly show stock quantity, so we will assume 1 for each item.
    TODO: If actual inventory quantity is available, implement extraction here.
    """
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

        # Inventory quantity is not shown on the page.
        # For prototype, assume inventory = 1 per item.
        inventory = 1  # TODO: Adjust if inventory data source is found.

        inventory_items.append(
            {
                "name": name,
                "description": description,
                "price": price,
                "inventory": inventory,
            }
        )
    return inventory_items


def analyze_products(products: list) -> dict:
    """
    Analyze products to generate summary:
    - total number of products
    - average price
    - highest priced item
    - lowest priced item
    - total inventory value
    """
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
    """
    Fire and forget task to login, scrape, analyze, and store summary.
    """
    global latest_summary

    try:
        logger.info(f"Job {job_id}: Starting data fetch and analysis")
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            html = await login_and_get_inventory(client)
        products = parse_inventory(html)
        summary = analyze_products(products)

        # Save summary to "persistent" cache
        latest_summary = summary

        entity_job[job_id]["status"] = "completed"
        entity_job[job_id]["completedAt"] = datetime.utcnow().isoformat()
        entity_job[job_id]["summary"] = summary
        logger.info(f"Job {job_id}: Completed successfully")

    except Exception as e:
        logger.exception(f"Job {job_id}: Failed with error")
        entity_job[job_id]["status"] = "failed"
        entity_job[job_id]["error"] = str(e)


@app.route("/api/fetch-and-analyze", methods=["POST"])
async def fetch_and_analyze():
    """
    POST endpoint to trigger login, scraping, and analysis workflow.
    Fires a background task and returns immediate job status.
    """
    requested_at = datetime.utcnow().isoformat()
    job_id = requested_at.replace(":", "-").replace(".", "-")

    entity_job[job_id] = {"status": "processing", "requestedAt": requested_at}

    # Fire and forget the processing task
    asyncio.create_task(process_entity(job_id))

    return jsonify(
        {
            "job_id": job_id,
            "status": "processing",
            "message": "Data fetch and analysis started",
        }
    )


@app.route("/api/report", methods=["GET"])
async def get_report():
    """
    GET endpoint to return the latest summary report in JSON.
    """
    if not latest_summary:
        return jsonify({"message": "No summary available yet"}), 404

    return jsonify(latest_summary)


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
    """
    Render the summary report page as HTML.
    """
    return await render_template_string(HTML_TEMPLATE, summary=latest_summary)


if __name__ == "__main__":
    import sys

    logging.basicConfig(stream=sys.stdout, level=logging.INFO)
    app.run(
        use_reloader=False, debug=True, host="0.0.0.0", port=8000, threaded=True
    )
```
