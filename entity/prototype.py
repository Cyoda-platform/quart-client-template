from dataclasses import dataclass
import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, Optional
import uuid

import httpx
from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request, validate_querystring

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# In-memory async-safe "databases"
trades: Dict[str, dict] = {}
legal_entities: Dict[str, dict] = {}
dtcc_messages: Dict[str, dict] = {}

# Dataclasses for request validation
@dataclass
class FpmlTradeRequest:
    fpmlMessage: str
    signature: Optional[str] = None

@dataclass
class LegalEntityRequest:
    lei: str
    name: str
    jurisdiction: str
    status: str

@dataclass
class LegalEntityQuery:
    lei: Optional[str] = None
    name: Optional[str] = None
    jurisdiction: Optional[str] = None

@dataclass
class DtccMessageRequest:
    tradeId: str
    messageType: str

# Constants for trade states and transitions
TRADE_STATES = {"draft", "confirmed", "amended", "cancelled", "rejected"}

# Utility: Generate ISO8601 UTC now
def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

# Mock validators and parsers
async def validate_fpml(fpml_message: str, signature: Optional[str]) -> bool:
    valid = bool(fpml_message and fpml_message.strip())
    if not valid:
        logger.info("FpML validation failed: empty message")
    return valid

async def verify_message_source() -> bool:
    return True

async def parse_fpml(fpml_message: str) -> dict:
    trade_id = str(uuid.uuid4())
    return {
        "tradeId": trade_id,
        "counterpartyLEI": "5493001KJTIIGC8Y1R12",
        "eventType": "tradeConfirmation",
        "tradeDetails": fpml_message[:100],
        "timestamp": utc_now_iso(),
    }

async def check_legal_entity_exists(lei: str) -> bool:
    return lei in legal_entities

def transition_trade_state(trade: dict, event_type: str) -> dict:
    current_state = trade.get("status", "draft")
    if event_type in ["execution", "newTrade"]:
        next_state = "draft"
    elif event_type == "tradeConfirmation" and current_state == "draft":
        next_state = "confirmed"
    elif event_type in ["amendment", "modification"] and current_state == "confirmed":
        next_state = "amended"
    elif event_type in ["cancel", "termination"]:
        next_state = "cancelled"
    elif event_type == "rejection" and current_state in ["draft", "confirmed"]:
        next_state = "rejected"
    else:
        next_state = current_state
    trade["status"] = next_state
    trade["lastUpdated"] = utc_now_iso()
    return trade

async def process_trade(trade_data: dict):
    trade_id = trade_data["tradeId"]
    try:
        lei = trade_data.get("counterpartyLEI")
        if not await check_legal_entity_exists(lei):
            trade_data["status"] = "rejected"
            trade_data["rejectionReason"] = f"Unknown legal entity LEI: {lei}"
        else:
            event_type = trade_data.get("eventType", "execution")
            trade_data = transition_trade_state(trades.get(trade_id, trade_data), event_type)
        trades[trade_id] = trade_data
        logger.info(f"Trade {trade_id} processed with status {trade_data['status']}")
    except Exception as e:
        logger.exception(e)

async def process_dtcc_message(dtcc_id: str):
    msg = dtcc_messages.get(dtcc_id)
    if not msg:
        logger.info(f"DTCC message {dtcc_id} not found")
        return
    try:
        await asyncio.sleep(1)
        msg["status"] = "sent"
        msg["sentAt"] = utc_now_iso()
        msg.setdefault("history", []).append({
            "timestamp": utc_now_iso(),
            "event": "sent",
            "details": "Mock DTCC message sent successfully",
        })
        logger.info(f"DTCC message {dtcc_id} sent")
    except Exception as e:
        msg["status"] = "failed"
        msg.setdefault("history", []).append({
            "timestamp": utc_now_iso(),
            "event": "failed",
            "details": str(e),
        })
        logger.exception(e)

@app.route("/trades/fpml", methods=["POST"])
# Workaround: due to quart-schema validate_request placement bug, route decorator first for POST
@validate_request(FpmlTradeRequest)
async def post_fpml_trade(data: FpmlTradeRequest):
    try:
        if not await validate_fpml(data.fpmlMessage, data.signature):
            return jsonify({"message": "FpML validation failed"}), 400
        if not await verify_message_source():
            return jsonify({"message": "Message source authentication failed"}), 401
        trade_data = await parse_fpml(data.fpmlMessage)
        trade_id = trade_data["tradeId"]
        trade_data["status"] = "draft"
        trade_data["createdAt"] = utc_now_iso()
        trades[trade_id] = trade_data
        asyncio.create_task(process_trade(trade_data))
        return jsonify({
            "tradeId": trade_id,
            "status": trade_data["status"],
            "message": "Trade received and processing started",
        })
    except Exception as e:
        logger.exception(e)
        return jsonify({"message": "Internal server error"}), 500

@validate_querystring(LegalEntityQuery)
@app.route("/legal-entities", methods=["GET"])
async def get_legal_entities():
    lei = request.args.get("lei")
    name = request.args.get("name")
    jurisdiction = request.args.get("jurisdiction")
    result = []
    for entity in legal_entities.values():
        if lei and entity["lei"] != lei:
            continue
        if name and name.lower() not in entity["name"].lower():
            continue
        if jurisdiction and entity["jurisdiction"] != jurisdiction:
            continue
        result.append(entity)
    return jsonify(result)

@app.route("/legal-entities", methods=["POST"])
# Workaround: validate_request last for POST
@validate_request(LegalEntityRequest)
async def post_legal_entity(data: LegalEntityRequest):
    try:
        legal_entities[data.lei] = {
            "lei": data.lei,
            "name": data.name,
            "jurisdiction": data.jurisdiction,
            "status": data.status,
            "updatedAt": utc_now_iso(),
        }
        return jsonify({"lei": data.lei, "message": "Legal entity added or updated successfully"})
    except Exception as e:
        logger.exception(e)
        return jsonify({"message": "Internal server error"}), 500

@app.route("/dtcc/messages", methods=["POST"])
# Workaround: validate_request last for POST
@validate_request(DtccMessageRequest)
async def post_dtcc_message(data: DtccMessageRequest):
    try:
        if data.tradeId not in trades:
            return jsonify({"message": f"Unknown tradeId {data.tradeId}"}), 400
        if data.messageType not in {"new", "modify", "cancel"}:
            return jsonify({"message": "Invalid messageType"}), 400
        dtcc_id = str(uuid.uuid4())
        dtcc_messages[dtcc_id] = {
            "dtccMessageId": dtcc_id,
            "tradeId": data.tradeId,
            "messageType": data.messageType,
            "status": "readyToSend",
            "createdAt": utc_now_iso(),
            "history": [],
        }
        asyncio.create_task(process_dtcc_message(dtcc_id))
        return jsonify({
            "dtccMessageId": dtcc_id,
            "status": "readyToSend",
            "message": "DTCC message generated and sending started",
        })
    except Exception as e:
        logger.exception(e)
        return jsonify({"message": "Internal server error"}), 500

@app.route("/dtcc/messages/<dtcc_id>/resend", methods=["POST"])
async def post_dtcc_message_resend(dtcc_id):
    try:
        msg = dtcc_messages.get(dtcc_id)
        if not msg:
            return jsonify({"message": "DTCC message not found"}), 404
        if msg["status"] == "sent":
            return jsonify({"message": "DTCC message already sent"}), 400
        msg["status"] = "readyToSend"
        msg.setdefault("history", []).append({
            "timestamp": utc_now_iso(),
            "event": "resendTriggered",
            "details": "Manual resend requested",
        })
        asyncio.create_task(process_dtcc_message(dtcc_id))
        return jsonify({
            "dtccMessageId": dtcc_id,
            "status": "readyToSend",
            "message": "Resend triggered",
        })
    except Exception as e:
        logger.exception(e)
        return jsonify({"message": "Internal server error"}), 500

@app.route("/dtcc/messages/<dtcc_id>", methods=["GET"])
async def get_dtcc_message(dtcc_id):
    msg = dtcc_messages.get(dtcc_id)
    if not msg:
        return jsonify({"message": "DTCC message not found"}), 404
    return jsonify(msg)

if __name__ == "__main__":
    import sys
    logging.basicConfig(
        stream=sys.stdout,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
        level=logging.INFO,
    )
    app.run(use_reloader=False, debug=True, host="0.0.0.0", port=8000, threaded=True)