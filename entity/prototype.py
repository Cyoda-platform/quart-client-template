```python
import asyncio
import logging
import uuid
from datetime import datetime
from typing import Dict, List, Optional

import httpx
from quart import Quart, request, jsonify
from quart_schema import QuartSchema

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# In-memory stores for prototype (async safe by design of asyncio single thread)
fpml_messages: Dict[str, dict] = {}
trades: Dict[str, dict] = {}
legal_entities: Dict[str, dict] = {}
dtcc_messages: Dict[str, dict] = {}

# Simulated external validation URLs (placeholders)
FPML_SCHEMA_VALIDATION_API = "https://www.mocky.io/v2/5185415ba171ea3a00704eed"  # mock "OK"
DTCC_TRANSMISSION_API = "https://httpbin.org/post"  # echo endpoint for transmission

# Utility functions
def now_iso() -> str:
    return datetime.utcnow().isoformat() + "Z"

async def validate_fpml_xml(fpml_xml: str) -> bool:
    # TODO: Replace with real FpML schema validation API
    async with httpx.AsyncClient() as client:
        try:
            # Mock call, always returns success for prototype
            resp = await client.get(FPML_SCHEMA_VALIDATION_API, timeout=5)
            return resp.status_code == 200
        except Exception as e:
            logger.exception("FpML schema validation failed")
            return False

async def transmit_dtcc_message(payload: dict) -> bool:
    # TODO: Implement real DTCC message transmission API call
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(DTCC_TRANSMISSION_API, json=payload, timeout=10)
            return resp.status_code == 200
        except Exception as e:
            logger.exception("DTCC message transmission failed")
            return False

# Processing tasks

async def process_fpml_message(message_id: str):
    msg = fpml_messages.get(message_id)
    if not msg:
        logger.error(f"FpMLMessage {message_id} not found for processing")
        return

    try:
        # Validate XML
        valid = await validate_fpml_xml(msg["payload"])
        if not valid:
            msg["status"] = "ERROR"
            msg["processingLog"].append({"timestamp": now_iso(), "event": "Validation failed"})
            logger.info(f"FpMLMessage {message_id} validation failed")
            return

        # Determine if matches existing trade (simplified heuristic)
        # TODO: Implement real matching logic based on payload parsing
        matched_trade_id = None
        for trade_id, trade in trades.items():
            if trade["tradeId"] in msg["payload"]:
                matched_trade_id = trade_id
                break

        if matched_trade_id is None:
            msg["status"] = "UNMATCHED"
            msg["processingLog"].append({"timestamp": now_iso(), "event": "No matching trade found"})
        else:
            msg["status"] = "MATCHED"
            msg["processingLog"].append({"timestamp": now_iso(), "event": f"Matched trade {matched_trade_id}"})

        # Transition to VALIDATED
        msg["status"] = "VALIDATED"
        msg["processingLog"].append({"timestamp": now_iso(), "event": "Validated"})

        # Create or update trade
        if matched_trade_id is None:
            # Create new trade
            trade_id = str(uuid.uuid4())
            trade = {
                "id": trade_id,
                "tradeId": f"trade-{trade_id[:8]}",
                "productType": "Unknown",  # TODO: Extract from FpML payload
                "party1LEI": "LEI0000001",  # TODO: Extract from FpML payload
                "party2LEI": "LEI0000002",  # TODO: Extract from FpML payload
                "tradeDetails": {},  # TODO: Extract from payload
                "status": "UNCONFIRMED",
                "originalFpMLMessageId": message_id,
                "events": [],
                "latestVersion": 1,
                "processingLog": [{"timestamp": now_iso(), "event": "Trade created"}],
            }
            trades[trade_id] = trade
            logger.info(f"Created new trade {trade_id} from FpMLMessage {message_id}")
        else:
            # Update existing trade (simplified)
            trade = trades[matched_trade_id]
            trade["latestVersion"] += 1
            trade["processingLog"].append({"timestamp": now_iso(), "event": "Trade updated from FpMLMessage"})
            logger.info(f"Updated trade {matched_trade_id} from FpMLMessage {message_id}")

        # Confirm trade (simulate external event)
        trade["status"] = "CONFIRMED"
        trade["processingLog"].append({"timestamp": now_iso(), "event": "Trade confirmed"})

        # Enrich trade with legal entity data
        # Check LegalEntityStatics exist for both LEIs
        lei1 = trade["party1LEI"]
        lei2 = trade["party2LEI"]
        if lei1 in legal_entities and lei2 in legal_entities:
            trade["processingLog"].append({"timestamp": now_iso(), "event": "Legal entity data enriched"})
        else:
            trade["status"] = "ERROR"
            trade["processingLog"].append({"timestamp": now_iso(), "event": "Missing LegalEntityStatics data"})
            logger.error(f"Missing LegalEntityStatics for trade {trade['id']}")
            return

        # Validate trade data (simplified)
        # TODO: Add detailed validation rules
        trade["status"] = "VALIDATED"
        trade["processingLog"].append({"timestamp": now_iso(), "event": "Trade data validated"})

        # Generate DTCC message
        dtcc_id = str(uuid.uuid4())
        dtcc_msg = {
            "id": dtcc_id,
            "type": "New Trade",
            "payload": {"tradeId": trade["tradeId"], "details": trade["tradeDetails"]},  # Simplified
            "status": "PENDING_TRANSMISSION",
            "creationTimestamp": now_iso(),
            "transmissionTimestamp": None,
            "acknowledgementTimestamp": None,
            "relatedTradeId": trade["id"],
            "processingLog": [{"timestamp": now_iso(), "event": "DTCC message created"}],
        }
        dtcc_messages[dtcc_id] = dtcc_msg
        logger.info(f"DTCCMessage {dtcc_id} created for trade {trade['id']}")

        # Transmit DTCC message
        sent = await transmit_dtcc_message(dtcc_msg["payload"])
        if sent:
            dtcc_msg["status"] = "TRANSMITTED"
            dtcc_msg["transmissionTimestamp"] = now_iso()
            dtcc_msg["processingLog"].append({"timestamp": now_iso(), "event": "Message transmitted"})
            logger.info(f"DTCCMessage {dtcc_id} transmitted")
            # Simulate acknowledgement reception
            dtcc_msg["status"] = "ACKNOWLEDGED"
            dtcc_msg["acknowledgementTimestamp"] = now_iso()
            dtcc_msg["processingLog"].append({"timestamp": now_iso(), "event": "Acknowledgement received"})
            # Update trade status accordingly
            trade["processingLog"].append({"timestamp": now_iso(), "event": "DTCC acknowledged"})
        else:
            dtcc_msg["status"] = "ERROR"
            dtcc_msg["processingLog"].append({"timestamp": now_iso(), "event": "Transmission error"})
            trade["status"] = "ERROR"
            trade["processingLog"].append({"timestamp": now_iso(), "event": "DTCC transmission failed"})
            logger.error(f"Failed to transmit DTCCMessage {dtcc_id}")

    except Exception as e:
        msg["status"] = "ERROR"
        msg["processingLog"].append({"timestamp": now_iso(), "event": "Processing exception"})
        logger.exception(f"Error processing FpMLMessage {message_id}: {e}")

async def process_legal_entity_upload(leis: List[dict]):
    for lei_rec in leis:
        lei = lei_rec.get("lei")
        if not lei:
            logger.warning("LegalEntityStatics record missing LEI")
            continue
        # TODO: Add validation of LEI format and fields here
        legal_entities[lei] = {
            "lei": lei,
            "legalName": lei_rec.get("legalName", ""),
            "address": lei_rec.get("address", ""),
            "countryCode": lei_rec.get("countryCode", ""),
            "status": "ACTIVE",
            "lastUpdated": now_iso(),
        }
        logger.info(f"LegalEntityStatics {lei} uploaded and activated")

# HTTP Endpoints

@app.route("/api/fpml-messages", methods=["POST"])
async def receive_fpml_message():
    data = await request.get_json()
    payload = data.get("payload")
    if not payload:
        return jsonify({"error": "Missing payload"}), 400
    message_id = str(uuid.uuid4())
    fpml_messages[message_id] = {
        "id": message_id,
        "payload": payload,
        "status": "PENDING",
        "receivedTimestamp": now_iso(),
        "processingLog": [{"timestamp": now_iso(), "event": "Received"}],
    }
    # Fire and forget processing task
    asyncio.create_task(process_fpml_message(message_id))
    return jsonify({"messageId": message_id, "status": "PENDING", "acknowledgement": "Received"}), 202

@app.route("/api/legal-entities", methods=["POST"])
async def upload_legal_entities():
    data = await request.get_json()
    if not isinstance(data, list):
        return jsonify({"error": "Expected a list of legal entity records"}), 400
    # Create entries with PENDING_UPLOAD status (simplified to ACTIVE after validation)
    # Fire and forget validation and activation
    asyncio.create_task(process_legal_entity_upload(data))
    return jsonify({"uploadedCount": len(data), "status": "PENDING_UPLOAD"}), 200

@app.route("/api/trades/<trade_id>", methods=["GET"])
async def get_trade(trade_id):
    trade = trades.get(trade_id)
    if not trade:
        return jsonify({"error": "Trade not found"}), 404
    return jsonify(trade), 200

@app.route("/api/dtcc-messages/<dtcc_id>", methods=["GET"])
async def get_dtcc_message(dtcc_id):
    msg = dtcc_messages.get(dtcc_id)
    if not msg:
        return jsonify({"error": "DTCCMessage not found"}), 404
    return jsonify(msg), 200

@app.route("/api/trades/<trade_id>/status", methods=["POST"])
async def update_trade_status(trade_id):
    trade = trades.get(trade_id)
    if not trade:
        return jsonify({"error": "Trade not found"}), 404
    data = await request.get_json()
    new_status = data.get("newStatus")
    event_details = data.get("eventDetails", {})
    if not new_status:
        return jsonify({"error": "Missing newStatus"}), 400
    # Update trade status and append event log
    trade["status"] = new_status
    trade["processingLog"].append({"timestamp": now_iso(), "event": f"Status updated externally: {new_status}", "details": event_details})
    logger.info(f"Trade {trade_id} status updated to {new_status}")
    return jsonify({"tradeId": trade_id, "updatedStatus": new_status}), 200


if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
```
