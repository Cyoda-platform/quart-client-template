import os
import asyncio
import logging
from datetime import datetime
from typing import List

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request

from common.config.config import ENTITY_VERSION
from app_init.app_init import entity_service, cyoda_token
from common.repository.cyoda.cyoda_init import init_cyoda

logger = logging.getLogger(__name__)

# Normalize product_data to a list of dictionaries.
async def process_normalize_products(entity: dict):
    raw_products = entity.get("product_data", [])
    products = []
    for prod in raw_products:
        if hasattr(prod, '__dict__'):
            products.append(prod.__dict__)
        elif isinstance(prod, dict):
            products.append(prod)
    if not products:
        entity["error"] = "No valid product data found"
    else:
        entity["products"] = products

# Build the report content from product data.
async def process_build_report_content(entity: dict):
    products = entity.get("products", [])
    report_content = "Product Report\n\n"
    categories = {}
    for product in products:
        cat = product.get("category", "Uncategorized")
        price_str = product.get("price", "$0").replace("$", "").strip()
        try:
            price = float(price_str)
        except Exception:
            price = 0.0
        categories.setdefault(cat, []).append(price)
        report_content += f"Product: {product.get('name', 'N/A')}\n"
        report_content += f"Price: {product.get('price', 'N/A')}\n"
        report_content += f"Category: {cat}\n"
        report_content += f"Comment Summary: {product.get('comment_summary', '')}\n\n"
    report_content += "Average Prices by Category:\n"
    for cat, prices in categories.items():
        avg_price = sum(prices) / len(prices) if prices else 0
        report_content += f"{cat}: ${avg_price:.2f}\n"
    entity["report_content"] = report_content

# Prepare the static folder where the report will be saved.
async def process_prepare_static_folder(entity: dict):
    static_folder = os.path.join(os.getcwd(), "static")
    if not os.path.exists(static_folder):
        try:
            os.makedirs(static_folder)
        except Exception as e:
            logger.exception(e)
            entity["error"] = "Failed to create static folder"
            return
    entity["static_folder"] = static_folder

# Save the report file to the static folder.
async def process_save_report_file(entity: dict):
    static_folder = entity.get("static_folder")
    report_content = entity.get("report_content", "")
    report_filename = "report.pdf"
    report_path = os.path.join(static_folder, report_filename)
    try:
        with open(report_path, "w") as f:
            f.write(report_content)
    except Exception as e:
        logger.exception(e)
        entity["error"] = "Failed to write report file"
        return
    entity["report_path"] = report_path

# Set the report URL and final processing details.
async def process_set_report_url(entity: dict):
    report_url = "http://localhost:8000/static/report.pdf"
    entity["report_url"] = report_url
    entity["processed"] = True
    entity["processed_at"] = datetime.utcnow().isoformat()