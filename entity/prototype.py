import os
import asyncio
import logging
import random
import string
from datetime import datetime

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema  # Only one-line setup as per requirements

app = Quart(__name__)
QuartSchema(app)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# In-memory caches for the prototype
scraped_products = {}
analysis_result = {}
report_result = {}

def generate_job_id():
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))

@app.route('/scrape-products', methods=['POST'])
async def scrape_products():
    payload = await request.get_json()
    url = payload.get('url')
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
            scraped_products['latest'] = products
            return jsonify({
                'status': 'success',
                'message': 'Products scraped successfully.',
                'data': products
            })
        except Exception as e:
            logger.exception(e)
            return jsonify({'status': 'error', 'message': 'Failed to scrape products.'}), 500

@app.route('/analyze-comments', methods=['POST'])
async def analyze_comments():
    payload = await request.get_json()
    comments = payload.get('comments')
    if not comments or not isinstance(comments, list):
        return jsonify({'status': 'error', 'message': 'Missing or invalid comments list'}), 400
    logger.info(f"Analyzing {len(comments)} comments")
    
    try:
        # Simple analysis: Count occurrences of positive and negative words.
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
        analysis_result['latest'] = result
        return jsonify(result)
    except Exception as e:
        logger.exception(e)
        return jsonify({'status': 'error', 'message': 'Failed to analyze comments.'}), 500

@app.route('/generate-report', methods=['POST'])
async def generate_report():
    payload = await request.get_json()
    product_data = payload.get('product_data')
    if not product_data or not isinstance(product_data, list):
        return jsonify({'status': 'error', 'message': 'Missing or invalid product_data.'}), 400
    logger.info("Generating PDF report")
    try:
        # For the prototype, generate a simple text file with a .pdf extension.
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
        
        # Save to a file in the static folder
        report_filename = "report.pdf"  # This is a text file with a .pdf extension for prototyping.
        report_path = os.path.join(app.static_folder, report_filename)
        with open(report_path, "w") as f:
            f.write(report_content)
        
        report_url = f"http://localhost:8000/static/{report_filename}"
        report_result['latest'] = report_url
        return jsonify({
            'status': 'success',
            'message': 'Report generated successfully.',
            'report_url': report_url
        })
    except Exception as e:
        logger.exception(e)
        return jsonify({'status': 'error', 'message': 'Failed to generate report.'}), 500

@app.route('/retrieve-report', methods=['GET'])
async def retrieve_report():
    report_url = report_result.get('latest')
    if not report_url:
        return jsonify({'status': 'error', 'message': 'No report available.'}), 404
    return jsonify({'status': 'success', 'report_url': report_url})

# Example background task using a fire-and-forget pattern.
async def process_entity(entity_job, data):
    # TODO: Expand this function for detailed job processing in a production environment.
    await asyncio.sleep(1)  # Simulate processing delay
    entity_job["status"] = "completed"
    logger.info("Finished processing entity job")

if __name__ == '__main__':
    # Set up the static folder to serve the generated report
    app.static_folder = os.path.join(os.getcwd(), "static")
    if not os.path.exists(app.static_folder):
        os.makedirs(app.static_folder)
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)