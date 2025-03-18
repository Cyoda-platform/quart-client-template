from common.grpc_client.grpc_client import grpc_stream
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
    app.background_task = asyncio.create_task(grpc_stream(cyoda_token))

@app.after_serving
async def shutdown():
    app.background_task.cancel()
    await app.background_task

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