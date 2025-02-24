from quart import Quart, request, jsonify
from quart_schema import QuartSchema
import aiohttp
import asyncio
import uuid
from app_init.app_init import entity_service

app = Quart(__name__)
QuartSchema(app)

async def fetch_conversion_rates():
    async with aiohttp.ClientSession() as session:
        return {
            "btc_usd_rate": "45000.00",
            "btc_eur_rate": "38000.00"
        }

@app.route('/reports', methods=['POST'])
async def create_report():
    data = await request.get_json()
    email = data.get('email')
    if not email:
        return jsonify({'error': 'Email is required.'}), 400
    rates = await fetch_conversion_rates()
    report_id = str(uuid.uuid4())
    report = {
        "report_id": report_id,
        "btc_usd_rate": rates["btc_usd_rate"],
        "btc_eur_rate": rates["btc_eur_rate"],
        "timestamp": "2023-10-01T12:00:00Z"
    }
    entity_service.add_item(
        token=token,
        entity_model="report",
        entity_version=ENTITY_VERSION,
        entity=report
    )
    print(f"Sending report to {email}...")
    return jsonify({
        "report_id": report_id,
        "status": "reporting"
    }), 202

@app.route('/reports/<report_id>', methods=['GET'])
async def get_report(report_id):
    report = entity_service.get_item(
        token=token,
        entity_model="report",
        entity_version=ENTITY_VERSION,
        technical_id=report_id
    )
    if not report:
        return jsonify({'error': 'Report not found.'}), 404
    return jsonify(report), 200

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)