from dataclasses import dataclass
import asyncio
import logging
import uuid
from datetime import datetime
from typing import Dict, List, Optional

import httpx
from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request, validate_querystring

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# Data classes for request validation
@dataclass
class FpMLMessageRequest:
    payload: str

@dataclass
class LegalEntityRecord:
    lei: str
    legalName: str
    address: str
    countryCode: str

@dataclass
class LegalEntityUpload:
    # Workaround: wrap list to allow validate_request on POST due to quart-schema issue
    entities: List[LegalEntityRecord]

@dataclass
class TradeStatusRequest:
    newStatus: str
    eventDetails: Optional[dict] = None

# In-memory stores for prototype
fpml_messages: Dict[str, dict] = {}
trades: Dict[str, dict] = {}
legal_entities: Dict[str, dict] = {}
dtcc_messages: Dict[str, dict] = {}

FPML_SCHEMA_VALIDATION_API = "https://www.mocky.io/v2/5185415ba171ea3a00704eed"
DTCC_TRANSMISSION_API = "https://httpbin.org/post"

def now_iso() -> str:
    return datetime.utcnow().isoformat() + "Z"

async def validate_fpml_xml(fpml_xml: str) -> bool:
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(FPML_SCHEMA_VALIDATION_API, timeout=5)
            return resp.status_code == 200
        except Exception as e:
            logger.exception("FpML schema validation failed")
            return False

async def transmit_dtcc_message(payload: dict) -> bool:
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(DTCC_TRANSMISSION_API, json=payload, timeout=10)
            return resp.status_code == 200
        except Exception as e:
            logger.exception("DTCC message transmission failed")
            return False

async def process_fpml_message(message_id: str):
    msg = fpml_messages.get(message_id)
    if not msg:
        logger.error(f"FpMLMessage {message_id} not found")
        return
    try:
        valid = await validate_fpml_xml(msg["payload"])
        if not valid:
            msg["status"] = "ERROR"
            msg["processingLog"].append({"timestamp": now_iso(), "event": "Validation failed"})
            return
        matched_trade_id = None
        for tid, trade in trades.items():
            if trade["tradeId"] in msg["payload"]:
                matched_trade_id = tid
                break
        if matched_trade_id is None:
            msg["status"] = "UNMATCHED"
            msg["processingLog"].append({"timestamp": now_iso(), "event": "No matching trade"})
        else:
            msg["status"] = "MATCHED"
            msg["processingLog"].append({"timestamp": now_iso(), "event": f"Matched {matched_trade_id}"})
        msg["status"] = "VALIDATED"
        msg["processingLog"].append({"timestamp": now_iso(), "event": "Validated"})
        if matched_trade_id is None:
            trade_id = str(uuid.uuid4())
            trade = {
                "id": trade_id,
                "tradeId": f"trade-{trade_id[:8]}",
                "productType": "Unknown",
                "party1LEI": "LEI0000001",
                "party2LEI": "LEI0000002",
                "tradeDetails": {},
                "status": "UNCONFIRMED",
                "originalFpMLMessageId": message_id,
                "events": [],
                "latestVersion": 1,
                "processingLog": [{"timestamp": now_iso(), "event": "Trade created"}],
            }
            trades[trade_id] = trade
        else:
            trade = trades[matched_trade_id]
            trade["latestVersion"] += 1
            trade["processingLog"].append({"timestamp": now_iso(), "event": "Trade updated"})
        trade["status"] = "CONFIRMED"
        trade["processingLog"].append({"timestamp": now_iso(), "event": "Confirmed"})
        lei1, lei2 = trade["party1LEI"], trade["party2LEI"]
        if lei1 in legal_entities and lei2 in legal_entities:
            trade["processingLog"].append({"timestamp": now_iso(), "event": "Enriched"})
        else:
            trade["status"] = "ERROR"
            trade["processingLog"].append({"timestamp": now_iso(), "event": "Missing LEI data"})
            return
        trade["status"] = "VALIDATED"
        trade["processingLog"].append({"timestamp": now_iso(), "event": "Validated trade"})
        dtcc_id = str(uuid.uuid4())
        dtcc_msg = {
            "id": dtcc_id,
            "type": "New Trade",
            "payload": {"tradeId": trade["tradeId"], "details": trade["tradeDetails"]},
            "status": "PENDING_TRANSMISSION",
            "creationTimestamp": now_iso(),
            "transmissionTimestamp": None,
            "acknowledgementTimestamp": None,
            "relatedTradeId": trade["id"],
            "processingLog": [{"timestamp": now_iso(), "event": "DTCC created"}],
        }
        dtcc_messages[dtcc_id] = dtcc_msg
        sent = await transmit_dtcc_message(dtcc_msg["payload"])
        if sent:
            dtcc_msg["status"] = "TRANSMITTED"
            dtcc_msg["transmissionTimestamp"] = now_iso()
            dtcc_msg["processingLog"].append({"timestamp": now_iso(), "event": "Transmitted"})
            dtcc_msg["status"] = "ACKNOWLEDGED"
            dtcc_msg["acknowledgementTimestamp"] = now_iso()
            dtcc_msg["processingLog"].append({"timestamp": now_iso(), "event": "Acknowledged"})
            trade["processingLog"].append({"timestamp": now_iso(), "event": "DTCC ack"})
        else:
            dtcc_msg["status"] = "ERROR"
            dtcc_msg["processingLog"].append({"timestamp": now_iso(), "event": "Transmission error"})
            trade["status"] = "ERROR"
            trade["processingLog"].append({"timestamp": now_iso(), "event": "DTCC failure"})
    except Exception as e:
        msg["status"] = "ERROR"
        msg["processingLog"].append({"timestamp": now_iso(), "event": "Exception"})
        logger.exception(e)

async def process_legal_entity_upload(records: List[LegalEntityRecord]):
    for rec in records:
        lei = rec.lei
        if not lei:
            continue
        legal_entities[lei] = {
            "lei": lei,
            "legalName": rec.legalName,
            "address": rec.address,
            "countryCode": rec.countryCode,
            "status": "ACTIVE",
            "lastUpdated": now_iso(),
        }

@app.route("/api/fpml-messages", methods=["POST"])
@validate_request(FpMLMessageRequest)  # Workaround: validation last for POST due to defect
async def receive_fpml_message(data: FpMLMessageRequest):
    message_id = str(uuid.uuid4())
    fpml_messages[message_id] = {
        "id": message_id,
        "payload": data.payload,
        "status": "PENDING",
        "receivedTimestamp": now_iso(),
        "processingLog": [{"timestamp": now_iso(), "event": "Received"}],
    }
    asyncio.create_task(process_fpml_message(message_id))
    return jsonify({"messageId": message_id, "status": "PENDING", "acknowledgement": "Received"}), 202

@app.route("/api/legal-entities", methods=["POST"])
@validate_request(LegalEntityUpload)  # Workaround: validation last for POST due to defect
async def upload_legal_entities(data: LegalEntityUpload):
    asyncio.create_task(process_legal_entity_upload(data.entities))
    return jsonify({"uploadedCount": len(data.entities), "status": "PENDING_UPLOAD"}), 200

@app.route("/api/trades/<trade_id>/status", methods=["POST"])
@validate_request(TradeStatusRequest)  # Workaround: validation last for POST due to defect
async def update_trade_status(data: TradeStatusRequest, trade_id):
    trade = trades.get(trade_id)
    if not trade:
        return jsonify({"error": "Trade not found"}), 404
    trade["status"] = data.newStatus
    trade["processingLog"].append({
        "timestamp": now_iso(),
        "event": f"Status updated: {data.newStatus}",
        "details": data.eventDetails or {}
    })
    return jsonify({"tradeId": trade_id, "updatedStatus": data.newStatus}), 200

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

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)