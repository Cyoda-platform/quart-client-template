#!/usr/bin/env python3
import os
import asyncio
import logging
import random
import string
from datetime import datetime
from dataclasses import dataclass
from typing import List

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request

from common.config.config import ENTITY_VERSION
from app_init.app_init import entity_service, cyoda_token
from common.repository.cyoda.cyoda_init import init_cyoda

app = Quart(__name__)
QuartSchema(app)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

def generate_job_id():
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))

# Data models for request validation

@dataclass
class ScrapeRequest:
    url: str

@dataclass
class AnalyzeRequest:
    comments: List[str]

@dataclass
class Product:
    name: str
    price: str
    category: str
    comment_summary: str = ""

@dataclass
class ReportRequest:
    product_data: List[Product]

@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)

# Workflow functions - all asynchronous processing for the respective entities is moved here.
# Each function takes the validated entity data as the only argument and returns the processed state.
# IMPORTANT: Do not use entity_service.add/update/delete on the current entity.

async def process_scraped_products(entity):
    # entity is expected to be a dict with a "url" key.
    # Validate input
    url = entity.get("url")
    if not url:
        entity["error"] = "Missing URL"
        return entity
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            # Here we get the page content if needed.
            html_content = response.text
    except Exception as e:
        logger.exception(e)
        entity["error"] = "Failed to retrieve URL"
        return entity
    # Simulate scraping logic (in real scenario, use html_content and an HTML parser or Selenium)
    products = [
        {
            "name": "Radiant Tee",
            "price": "$22.00",
            "category": "Apparel",
            "comments": ["Great quality!", "Comfortable fit."],
            "processed_at": datetime.utcnow().isoformat()
        },
        {
            "name": "Breathe-Easy Tank",
            "price": "$34.00",
            "category": "Apparel",
            "comments": ["Stylish and durable."],
            "processed_at": datetime.utcnow().isoformat()
        }
    ]
    # Return the list of scraped products as the new state of the entity.
    return products

async def process_analysis_result(entity):
    # entity is expected to be a dict with a "comments" key.
    comments = entity.get("comments", [])
    if not isinstance(comments, list):
        entity["error"] = "Invalid comments data"
        return entity
    positive_words = ['great', 'good', 'excellent', 'positive', 'stylish', 'comfortable']
    negative_words = ['bad', 'poor', 'terrible', 'negative']
    positive_count = 0
    negative_count = 0
    for comment in comments:
        lc = comment.lower()
        for word in positive_words:
            if word in lc:
                positive_count += 1
        for word in negative_words:
            if word in lc:
                negative_count += 1
    summary = "Mixed feedback"
    if positive_count > negative_count:
        summary = "Overall positive feedback"
    elif negative_count > positive_count:
        summary = "Overall negative feedback"
    result = {
        "status": "success",
        "summary": summary,
        "sentiment": {
            "positive": positive_count,
            "negative": negative_count
        },
        "processed_at": datetime.utcnow().isoformat()
    }
    return result

async def process_report_result(entity):
    # entity is expected to be a dict with a "product_data" key.
    # Normalize product_data, converting dataclass instances to dict if needed.
    raw_products = entity.get("product_data", [])
    products = []
    for prod in raw_products:
        if hasattr(prod, '__dict__'):
            products.append(prod.__dict__)
        elif isinstance(prod, dict):
            products.append(prod)
    if not products:
        return {"error": "No valid product data found"}
    report_content = "Product Report\n\n"
    categories = {}
    # Build report content and accumulate pricing info.
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
    
    # Ensure the static folder exists
    static_folder = app.static_folder or os.path.join(os.getcwd(), "static")
    if not os.path.exists(static_folder):
        try:
            os.makedirs(static_folder)
        except Exception as e:
            logger.exception(e)
            return {"error": "Failed to create static folder"}
    # Save report to a file in the static folder.
    report_filename = "report.pdf"  # For prototyping, this is a text file with a .pdf extension.
    report_path = os.path.join(static_folder, report_filename)
    try:
        with open(report_path, "w") as f:
            f.write(report_content)
    except Exception as e:
        logger.exception(e)
        return {"error": "Failed to write report file"}
    
    report_url = f"http://localhost:8000/static/{report_filename}"
    return {
        "report_url": report_url,
        "processed": True,
        "processed_at": datetime.utcnow().isoformat()
    }

@app.route('/scrape-products', methods=['POST'])
@validate_request(ScrapeRequest)
async def scrape_products(data: ScrapeRequest):
    # Pass minimal data (the URL) to the workflow function.
    # The workflow function will perform actual scraping asynchronously.
    job_id = await entity_service.add_item(
        token=cyoda_token,
        entity_model="scraped_products",
        entity_version=ENTITY_VERSION,  # always use this constant
        entity={"url": data.url},
        workflow=process_scraped_products  # Workflow function applied asynchronously before persistence.
    )
    return jsonify({
        'status': 'success',
        'job_id': job_id,
        'message': 'Products scraping has been initiated. Retrieve results using the job ID.'
    })

@app.route('/analyze-comments', methods=['POST'])
@validate_request(AnalyzeRequest)
async def analyze_comments(data: AnalyzeRequest):
    # Pass the comments list to the workflow function for asynchronous processing.
    job_id = await entity_service.add_item(
        token=cyoda_token,
        entity_model="analysis_result",
        entity_version=ENTITY_VERSION,  # always use this constant
        entity=data.__dict__,
        workflow=process_analysis_result  # Workflow function applied asynchronously before persistence.
    )
    return jsonify({
        'status': 'success',
        'job_id': job_id,
        'message': 'Comments analysis has been initiated. Retrieve results using the job ID.'
    })

@app.route('/generate-report', methods=['POST'])
@validate_request(ReportRequest)
async def generate_report(data: ReportRequest):
    # Pass product data to the workflow function for report generation.
    job_id = await entity_service.add_item(
        token=cyoda_token,
        entity_model="report_result",
        entity_version=ENTITY_VERSION,  # always use this constant
        entity=data.__dict__,
        workflow=process_report_result  # Workflow function applied asynchronously before persistence.
    )
    return jsonify({
        'status': 'success',
        'job_id': job_id,
        'message': 'Report generation has been initiated. Retrieve report using the job ID.'
    })

@app.route('/retrieve-report', methods=['GET'])
async def retrieve_report():
    tech_id = request.args.get("id")
    if not tech_id:
        return jsonify({'status': 'error', 'message': 'Missing id parameter.'}), 400
    try:
        report = await entity_service.get_item(
            token=cyoda_token,
            entity_model="report_result",
            entity_version=ENTITY_VERSION,  # always use this constant
            technical_id=tech_id
        )
        if not report:
            return jsonify({'status': 'error', 'message': 'No report found for the provided id.'}), 404
        return jsonify({'status': 'success', 'report': report})
    except Exception as e:
        logger.exception(e)
        return jsonify({'status': 'error', 'message': 'Failed to retrieve report.'}), 500

if __name__ == '__main__':
    # Set up the static folder to serve the generated report
    app.static_folder = os.path.join(os.getcwd(), "static")
    if not os.path.exists(app.static_folder):
        os.makedirs(app.static_folder)
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)