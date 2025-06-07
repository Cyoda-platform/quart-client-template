```python
import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, Optional
import uuid

import httpx
from quart import Quart, request, jsonify
from quart_schema import QuartSchema

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# In-memory async-safe "databases"
trades: Dict[str, dict] = {}
legal_entities: Dict[str, dict] = {}
dtcc_messages: Dict[str, dict] = {}

# Trade states and transitions (simplified enforcement in prototype)
TRADE_STATES = {"draft", "confirmed", "amended", "cancelled", "rejected"}
TRADE_TRANSITIONS = {
    "execution": ("draft",),
    "newTrade": ("draft",),
    "tradeConfirmation": ("draft", "confirmed"),
    "amendment": ("confirmed", "amended"),
    "modification": ("confirmed", "amended"),
    "cancel": ("draft", "confirmed", "amended", "cancelled"),
    "termination": ("draft", "confirmed", "amended", "cancelled"),
    "rejection": ("draft", "confirmed", "rejected"),
}


# Utility: Generate ISO8601 UTC now
def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# Mock: Validate FpML schema and signature (TODO: implement real validation)
async def validate_fpml(fpml_message: str, signature: Optional[str]) -> bool:
    # TODO: Real FpML schema validation & digital signature verification.
    # Here, just check if message is non-empty string.
    valid = bool(fpml_message and fpml_message.strip())
    if not valid:
        logger.info("FpML validation failed: empty message")
    return valid


# Mock: Verify message source authenticity (TODO: implement real mTLS/signature check)
async def verify_message_source() -> bool:
    # TODO: Real mTLS or signed payload verification required here.
    return True


# Mock: Parse FpML XML message (TODO: parse XML properly)
async def parse_fpml(fpml_message: str) -> dict:
    # TODO: Parse FpML XML and extract trade data fields.
    # Prototype returns dummy data with random tradeId.
    trade_id = str(uuid.uuid4())
    trade_data = {
        "tradeId": trade_id,
        "counterpartyLEI": "5493001KJTIIGC8Y1R12",  # Example LEI
        "eventType": "tradeConfirmation",
        "tradeDetails": fpml_message[:100],  # just snippet for demo
        "timestamp": utc_now_iso(),
    }
    return trade_data


# Check legal entity exists by LEI
async def check_legal_entity_exists(lei: str) -> bool:
    return lei in legal_entities


# Workflow: Transition trade state according to event
def transition_trade_state(trade: dict, event_type: str) -> dict:
    current_state = trade.get("status", "draft")
    # Determine next state based on event and current state
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
        # No valid transition, keep current state
        next_state = current_state
    trade["status"] = next_state
    trade["lastUpdated"] = utc_now_iso()
    return trade


# Async processing task for trades (fire-and-forget)
async def process_trade(trade_data: dict):
    trade_id = trade_data["tradeId"]
    try:
        # Validate legal entity
        lei = trade_data.get("counterpartyLEI")
        if not await check_legal_entity_exists(lei):
            logger.info(f"Trade {trade_id} references unknown legal entity LEI={lei}")
            trade_data["status"] = "rejected"
            trade_data["rejectionReason"] = f"Unknown legal entity LEI: {lei}"
        else:
            # Transition trade state based on eventType
            event_type = trade_data.get("eventType", "execution")
            trade_data = transition_trade_state(trades.get(trade_id, trade_data), event_type)

        trades[trade_id] = trade_data
        logger.info(f"Trade {trade_id} processed with status {trade_data['status']}")
    except Exception as e:
        logger.exception(e)


# Async processing task for DTCC message sending (mock)
async def process_dtcc_message(dtcc_id: str):
    msg = dtcc_messages.get(dtcc_id)
    if not msg:
        logger.info(f"DTCC message {dtcc_id} not found for processing")
        return

    try:
        # Mock sending delay
        await asyncio.sleep(1)
        # Mock sending success or failure randomly
        # For prototype: always success
        msg["status"] = "sent"
        msg["sentAt"] = utc_now_iso()
        msg.setdefault("history", []).append(
            {
                "timestamp": utc_now_iso(),
                "event": "sent",
                "details": "Mock DTCC message sent successfully",
            }
        )
        logger.info(f"DTCC message {dtcc_id} sent successfully")
    except Exception as e:
        msg["status"] = "failed"
        msg.setdefault("history", []).append(
            {
                "timestamp": utc_now_iso(),
                "event": "failed",
                "details": str(e),
            }
        )
        logger.exception(e)


@app.route("/trades/fpml", methods=["POST"])
async def post_fpml_trade():
    try:
        data = await request.get_json()
        fpml_message = data.get("fpmlMessage")
        signature = data.get("signature")

        if not await validate_fpml(fpml_message, signature):
            return jsonify({"message": "FpML validation failed"}), 400

        if not await verify_message_source():
            return jsonify({"message": "Message source authentication failed"}), 401

        trade_data = await parse_fpml(fpml_message)
        trade_id = trade_data["tradeId"]

        # Save initial trade data with draft status
        trade_data["status"] = "draft"
        trade_data["createdAt"] = utc_now_iso()
        trades[trade_id] = trade_data

        # Fire and forget trade processing (state transitions etc.)
        asyncio.create_task(process_trade(trade_data))

        return jsonify(
            {
                "tradeId": trade_id,
                "status": trade_data["status"],
                "message": "Trade received and processing started",
            }
        )
    except Exception as e:
        logger.exception(e)
        return jsonify({"message": "Internal server error"}), 500


@app.route("/legal-entities", methods=["GET"])
async def get_legal_entities():
    lei = request.args.get("lei")
    name = request.args.get("name")
    jurisdiction = request.args.get("jurisdiction")

    # Simple filtering
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
async def post_legal_entity():
    try:
        data = await request.get_json()
        lei = data.get("lei")
        if not lei:
            return jsonify({"message": "LEI is required"}), 400

        # Add or update
        legal_entities[lei] = {
            "lei": lei,
            "name": data.get("name", ""),
            "jurisdiction": data.get("jurisdiction", ""),
            "status": data.get("status", "active"),
            "updatedAt": utc_now_iso(),
        }
        return jsonify({"lei": lei, "message": "Legal entity added or updated successfully"})
    except Exception as e:
        logger.exception(e)
        return jsonify({"message": "Internal server error"}), 500


@app.route("/dtcc/messages", methods=["POST"])
async def post_dtcc_message():
    try:
        data = await request.get_json()
        trade_id = data.get("tradeId")
        message_type = data.get("messageType")

        if trade_id not in trades:
            return jsonify({"message": f"Unknown tradeId {trade_id}"}), 400

        if message_type not in {"new", "modify", "cancel"}:
            return jsonify({"message": "Invalid messageType"}), 400

        dtcc_id = str(uuid.uuid4())
        dtcc_message = {
            "dtccMessageId": dtcc_id,
            "tradeId": trade_id,
            "messageType": message_type,
            "status": "readyToSend",
            "createdAt": utc_now_iso(),
            "history": [],
        }
        dtcc_messages[dtcc_id] = dtcc_message

        # Fire and forget sending task (mock)
        asyncio.create_task(process_dtcc_message(dtcc_id))

        return jsonify(
            {
                "dtccMessageId": dtcc_id,
                "status": dtcc_message["status"],
                "message": "DTCC message generated and sending started",
            }
        )
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
        msg.setdefault("history", []).append(
            {
                "timestamp": utc_now_iso(),
                "event": "resendTriggered",
                "details": "Manual resend requested",
            }
        )

        # Fire and forget resend task
        asyncio.create_task(process_dtcc_message(dtcc_id))
        return jsonify(
            {
                "dtccMessageId": dtcc_id,
                "status": "readyToSend",
                "message": "Resend triggered",
            }
        )
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
```
