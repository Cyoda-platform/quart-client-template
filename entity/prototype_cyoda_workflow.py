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

# Removed local in‐memory caches since we now use external entity_service

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

# Workflow functions - each function name must have a prefix "process_" followed by the entity name.

async def process_scraped_products(entity):
    # Example: Add a processed timestamp to each product in the list.
    await asyncio.sleep(0.1)  # Simulate asynchronous processing delay
    if isinstance(entity, list):
        for item in entity:
            item["processed_at"] = datetime.utcnow().isoformat()
    return entity

async def process_analysis_result(entity):
    # Example: Mark analysis result as processed and add a timestamp.
    await asyncio.sleep(0.1)
    if isinstance(entity, dict):
        entity["workflow_processed"] = True
        entity["processed_at"] = datetime.utcnow().isoformat()
    return entity

async def process_report_result(entity):
    # Example: Wrap the report URL into a dict and add processing info.
    await asyncio.sleep(0.1)
    return {
        "report_url": entity,
        "processed": True,
        "processed_at": datetime.utcnow().isoformat()
    }

@app.route('/scrape-products', methods=['POST'])
@validate_request(ScrapeRequest)
async def scrape_products(data: ScrapeRequest):
    url = data.url
    if not url:
        return jsonify({'status': 'error', 'message': 'Missing URL'}), 400
    logger.info(f"Scraping products from URL: {url}")
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url)
            html_content = response.text
            # TODO: Use Selenium or another JavaScript-rendering solution to extract product data.
            # For this prototype, return a static/mock response.
            products = [
                {
                    "name": "Radiant Tee",
                    "price": "$22.00",
                    "category": "Apparel",
                    "comments": ["Great quality!", "Comfortable fit."]
                },
                {
                    "name": "Breathe-Easy Tank",
                    "price": "$34.00",
                    "category": "Apparel",
                    "comments": ["Stylish and durable."]
                }
            ]
            # Replace local cache storage with an external service call
            job_id = await entity_service.add_item(
                token=cyoda_token,
                entity_model="scraped_products",
                entity_version=ENTITY_VERSION,  # always use this constant
                entity=products,
                workflow=process_scraped_products  # Workflow function applied asynchronously before persistence
            )
            return jsonify({
                'status': 'success',
                'job_id': job_id,
                'message': 'Products scraping initiated. Retrieve results using the job ID.'
            })
        except Exception as e:
            logger.exception(e)
            return jsonify({'status': 'error', 'message': 'Failed to scrape products.'}), 500

@app.route('/analyze-comments', methods=['POST'])
@validate_request(AnalyzeRequest)
async def analyze_comments(data: AnalyzeRequest):
    comments = data.comments
    if not comments or not isinstance(comments, list):
        return jsonify({'status': 'error', 'message': 'Missing or invalid comments list'}), 400
    logger.info(f"Analyzing {len(comments)} comments")
    try:
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
            }
        }
        job_id = await entity_service.add_item(
            token=cyoda_token,
            entity_model="analysis_result",
            entity_version=ENTITY_VERSION,  # always use this constant
            entity=result,
            workflow=process_analysis_result  # Workflow function applied asynchronously before persistence
        )
        return jsonify({
            'status': 'success',
            'job_id': job_id,
            'message': 'Comments analysis initiated. Retrieve results using the job ID.'
        })
    except Exception as e:
        logger.exception(e)
        return jsonify({'status': 'error', 'message': 'Failed to analyze comments.'}), 500

@app.route('/generate-report', methods=['POST'])
@validate_request(ReportRequest)
async def generate_report(data: ReportRequest):
    product_data = [p.__dict__ for p in data.product_data]
    if not product_data or not isinstance(product_data, list):
        return jsonify({'status': 'error', 'message': 'Missing or invalid product_data.'}), 400
    logger.info("Generating PDF report")
    try:
        report_content = "Product Report\n\n"
        categories = {}
        for product in product_data:
            cat = product.get("category", "Uncategorized")
            price_str = product.get("price", "$0").replace("$", "")
            try:
                price = float(price_str)
            except Exception:
                price = 0.0
            categories.setdefault(cat, []).append(price)
            report_content += f"Product: {product.get('name')}\n"
            report_content += f"Price: {product.get('price')}\n"
            report_content += f"Category: {cat}\n"
            report_content += f"Comment Summary: {product.get('comment_summary', '')}\n\n"
        report_content += "Average Prices by Category:\n"
        for cat, prices in categories.items():
            avg_price = sum(prices) / len(prices) if prices else 0
            report_content += f"{cat}: ${avg_price:.2f}\n"
        
        # Save report to a file in the static folder
        report_filename = "report.pdf"  # This is a text file with a .pdf extension for prototyping.
        report_path = os.path.join(app.static_folder, report_filename)
        with open(report_path, "w") as f:
            f.write(report_content)
        
        report_url = f"http://localhost:8000/static/{report_filename}"
        job_id = await entity_service.add_item(
            token=cyoda_token,
            entity_model="report_result",
            entity_version=ENTITY_VERSION,  # always use this constant
            entity=report_url,
            workflow=process_report_result  # Workflow function applied asynchronously before persistence
        )
        return jsonify({
            'status': 'success',
            'job_id': job_id,
            'message': 'Report generation initiated. Retrieve report using the job ID.'
        })
    except Exception as e:
        logger.exception(e)
        return jsonify({'status': 'error', 'message': 'Failed to generate report.'}), 500

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
        return jsonify({'status': 'success', 'report_url': report})
    except Exception as e:
        logger.exception(e)
        return jsonify({'status': 'error', 'message': 'Failed to retrieve report.'}), 500

# Example background task using a fire-and-forget pattern.
async def process_entity(entity_job, data):
    await asyncio.sleep(1)  # Simulate processing delay
    entity_job["status"] = "completed"
    logger.info("Finished processing entity job")

if __name__ == '__main__':
    # Set up the static folder to serve the generated report
    app.static_folder = os.path.join(os.getcwd(), "static")
    if not os.path.exists(app.static_folder):
        os.makedirs(app.static_folder)
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)