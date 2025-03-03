import asyncio
import uuid
from datetime import datetime

import httpx
from quart import Quart, request, jsonify
from quart_schema import QuartSchema

app = Quart(__name__)
QuartSchema(app)

# In-memory storage for reports
reports = {}

async def fetch_conversion_rate(symbol: str) -> float:
    # Use Binance API as external source
    url = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}"
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        # TODO: Add error handling for non-200 responses or malformed data
        data = response.json()
        return float(data.get("price", 0.0))

async def send_email(recipient: str, report: dict):
    # TODO: Replace with actual email sending integration
    print(f"Sending email to {recipient} with report: {report}")
    await asyncio.sleep(0.1)  # Simulate email sending delay

async def process_entity(job_id: str, recipient: str):
    requested_at = datetime.utcnow().isoformat() + "Z"
    # Store initial processing state
    reports[job_id] = {"status": "processing", "requestedAt": requested_at}

    try:
        # Fetch conversion rates for BTC/USD and BTC/EUR
        btc_usd = await fetch_conversion_rate("BTCUSDT")
        btc_eur = await fetch_conversion_rate("BTCEUR")  # TODO: Verify if BTCEUR is supported by the API
    except Exception as e:
        # TODO: Implement more robust error handling and logging
        reports[job_id] = {"status": "error", "error": str(e), "requestedAt": requested_at}
        return

    timestamp = datetime.utcnow().isoformat() + "Z"
    report = {
        "report_id": job_id,
        "status": "success",
        "conversionRates": {
            "BTC_USD": btc_usd,
            "BTC_EUR": btc_eur
        },
        "timestamp": timestamp,
        "email_sent": False
    }

    # Send email report (fire and forget pattern)
    await send_email(recipient, report)
    report["email_sent"] = True

    # Update the in-memory report with final details
    reports[job_id] = report

@app.route("/job", methods=["POST"])
async def create_job():
    data = await request.get_json()
    recipient = data.get("recipient")
    if not recipient:
        return jsonify({"error": "Recipient email is required"}), 400

    job_id = str(uuid.uuid4())

    # Fire and forget the processing task.
    # In a real implementation, you might not await the task immediately.
    task = asyncio.create_task(process_entity(job_id, recipient))
    await task

    return jsonify(reports[job_id]), 200

@app.route("/report/<job_id>", methods=["GET"])
async def get_report(job_id):
    report = reports.get(job_id)
    if not report:
        return jsonify({"error": "Report not found"}), 404
    return jsonify(report), 200

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)