from quart import Quart, request, jsonify
from quart_schema import QuartSchema
import aiohttp
import uuid
import asyncio
from app_init.app_init import entity_service

app = Quart(__name__)
QuartSchema(app)
CONVERSION_API_URL = "https://api.example.com/v1/btc/rates"

async def fetch_conversion_rates():
    async with aiohttp.ClientSession() as session:
        async with session.get(CONVERSION_API_URL) as response:
            data = await response.json()
            return {"btc_usd": data.get("btc_usd", 50000), "btc_eur": data.get("btc_eur", 42000)}

@app.route('/jobs', methods=['POST'])
async def create_report():
    data = await request.get_json()
    email = data.get('email')
    job_id = str(uuid.uuid4())
    rates = await fetch_conversion_rates()
    report = {
        "id": job_id,
        "btc_usd": rates["btc_usd"],
        "btc_eur": rates["btc_eur"],
        "timestamp": "2023-10-01T12:00:00Z"
    }
    entity_service.add_item(token=token, entity_model="report", entity_version=ENTITY_VERSION, entity=report)
    return jsonify({"job_id": job_id, "status": "processing"}), 202

@app.route('/reports/<id>', methods=['GET'])
async def get_report(id):
    report = entity_service.get_item(token=token, entity_model="report", entity_version=ENTITY_VERSION, technical_id=id)
    if report:
        return jsonify(report), 200
    return jsonify({"error": "Report not found"}), 404

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)