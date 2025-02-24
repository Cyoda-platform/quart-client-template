from quart import Quart, request, jsonify
from quart_schema import QuartSchema
import aiohttp
import uuid
import datetime
from app_init.app_init import entity_service

app = Quart(__name__)
QuartSchema(app)

async def fetch_btc_rates():
    async with aiohttp.ClientSession() as session:
        btc_usd_rate = "45000.00"
        btc_eur_rate = "38000.00"
        return btc_usd_rate, btc_eur_rate

@app.route('/reports', methods=['POST'])
async def create_report():
    data = await request.get_json()
    email = data.get("email")
    btc_usd_rate, btc_eur_rate = await fetch_btc_rates()
    report_id = str(uuid.uuid4())
    timestamp = datetime.datetime.utcnow().isoformat() + "Z"
    report = {
        "report_id": report_id,
        "btc_usd_rate": btc_usd_rate,
        "btc_eur_rate": btc_eur_rate,
        "timestamp": timestamp,
        "status": "reporting"
    }
    entity_service.add_item(
        token=token,
        entity_model="report",
        entity_version=ENTITY_VERSION,
        entity=report
    )
    return jsonify({"report_id": report_id, "status": "reporting"}), 202

@app.route('/reports/<report_id>', methods=['GET'])
async def get_report(report_id):
    report = entity_service.get_item(
        token=token,
        entity_model="report",
        entity_version=ENTITY_VERSION,
        technical_id=report_id
    )
    if not report:
        return jsonify({"error": "Report not found"}), 404
    return jsonify(report), 200

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)