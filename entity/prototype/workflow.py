import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime

import httpx

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

async def process_login(entity: dict) -> str:
    """
    Logs into SauceDemo and returns inventory page HTML.
    """
    SAUCEDEMO_LOGIN_URL = "https://www.saucedemo.com/"
    SAUCEDEMO_INVENTORY_URL = "https://www.saucedemo.com/inventory.html"
    USERNAME = "standard_user"
    PASSWORD = "secret_sauce"

    async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
        r1 = await client.get(SAUCEDEMO_LOGIN_URL)
        r1.raise_for_status()
        login_data = {"user-name": USERNAME, "password": PASSWORD}
        r2 = await client.post(SAUCEDEMO_LOGIN_URL, data=login_data, follow_redirects=True)
        r2.raise_for_status()
        r3 = await client.get(SAUCEDEMO_INVENTORY_URL)
        r3.raise_for_status()
        return r3.text

def process_parse_inventory(entity: dict, html: str) -> list:
    """
    Parse inventory page HTML and set products list to entity['products'].
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
        inventory = 1  # TODO: adjust if actual stock quantity is discoverable
        inventory_items.append({"name": name, "description": description, "price": price, "inventory": inventory})
    entity["products"] = inventory_items
    return inventory_items

def process_analyze(entity: dict, products: list) -> dict:
    """
    Analyze product list and set summary to entity['summary'].
    """
    if not products:
        summary = {}
    else:
        total_products = len(products)
        total_price = sum(p["price"] for p in products)
        average_price = total_price / total_products
        highest = max(products, key=lambda p: p["price"])
        lowest = min(products, key=lambda p: p["price"])
        total_inventory_value = sum(p["price"] * p["inventory"] for p in products)
        summary = {
            "total_products": total_products,
            "average_price": round(average_price, 2),
            "highest_priced_item": {"name": highest["name"], "price": highest["price"]},
            "lowest_priced_item": {"name": lowest["name"], "price": lowest["price"]},
            "total_inventory_value": round(total_inventory_value, 2),
        }
    entity["summary"] = summary
    return summary

async def process_prototype(entity: dict):
    """
    Workflow orchestration function.
    Modifies entity in-place, no additional arguments.
    """
    job_id = entity.get("technical_id") or entity.get("id") or entity.get("job_id")
    if not job_id:
        logger.error("process_prototype: No job id found in entity")
        entity["status"] = "failed"
        entity["error"] = "Missing job id"
        return

    try:
        logger.info(f"Job {job_id}: Starting data fetch and analysis")
        html = await process_login(entity)
        products = process_parse_inventory(entity, html)
        process_analyze(entity, products)
        entity["status"] = "completed"
        entity["completedAt"] = datetime.utcnow().isoformat()
        logger.info(f"Job {job_id}: Completed successfully")
    except Exception as e:
        logger.exception(f"Job {job_id}: Failed with error")
        entity["status"] = "failed"
        entity["error"] = str(e)