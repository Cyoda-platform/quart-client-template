from dataclasses import dataclass
import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional
import uuid

import httpx
from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request, validate_querystring

from app_init.app_init import BeanFactory
from common.config.config import ENTITY_VERSION

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

factory = BeanFactory(config={'CHAT_REPOSITORY': 'cyoda'})
entity_service = factory.get_services()['entity_service']
cyoda_auth_service = factory.get_services()["cyoda_auth_service"]

app = Quart(__name__)
QuartSchema(app)

# Dataclasses for request validation
@dataclass
class Fpml_trade_request:
    fpmlMessage: str
    signature: Optional[str] = None

@dataclass
class Legal_entity_request:
    lei: str
    name: str
    jurisdiction: str
    status: str

@dataclass
class Legal_entity_query:
    lei: Optional[str] = None
    name: Optional[str] = None
    jurisdiction: Optional[str] = None

@dataclass
class Dtcc_message_request:
    tradeId: str
    messageType: str

TRADE_STATES = {"draft", "confirmed", "amended", "cancelled", "rejected"}

def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

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
    condition = {
        "cyoda": {
            "type": "group",
            "operator": "AND",
            "conditions": [
                {
                    "jsonPath": "lei",
                    "operatorType": "EQUALS",
                    "value": lei,
                    "type": "simple"
                }
            ]
        }
    }
    items = await entity_service.get_items_by_condition(
        token=cyoda_auth_service,
        entity_model="legal_entity",
        entity_version=ENTITY_VERSION,
        condition=condition
    )
    return bool(items)

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
    """
    Full trade processing before persistence:
    - Check legal entity existence
    - Transition trade state
    - Set rejection reason if needed
    """
    try:
        lei = trade_data.get("counterpartyLEI")
        if not await check_legal_entity_exists(lei):
            trade_data["status"] = "rejected"
            trade_data["rejectionReason"] = f"Unknown legal entity LEI: {lei}"
        else:
            event_type = trade_data.get("eventType", "execution")
            existing_trade = await entity_service.get_item(
                token=cyoda_auth_service,
                entity_model="trade",
                entity_version=ENTITY_VERSION,
                technical_id=trade_data.get("tradeId")
            ) or {}
            transition_trade_state(existing_trade or trade_data, event_type)
        trade_data["lastProcessedAt"] = utc_now_iso()
    except Exception as e:
        logger.exception(f"Error in process_trade workflow: {e}")

async def process_legal_entity(legal_entity_data: dict):
    """
    Workflow function for legal_entity, update timestamp before persistence
    """
    legal_entity_data["updatedAt"] = utc_now_iso()

async def process_dtcc_message(dtcc_data: dict):
    """
    Full DTCC message sending simulation before persistence:
    - Add status, createdAt if missing
    - Simulate sending delay
    - Update status to sent or failed accordingly
    - Append to history
    """
    if "status" not in dtcc_data:
        dtcc_data["status"] = "readyToSend"
    if "createdAt" not in dtcc_data:
        dtcc_data["createdAt"] = utc_now_iso()
    dtcc_id = dtcc_data.get("dtccMessageId")
    try:
        await asyncio.sleep(1)
        dtcc_data["status"] = "sent"
        dtcc_data["sentAt"] = utc_now_iso()
        dtcc_data.setdefault("history", []).append({
            "timestamp": utc_now_iso(),
            "event": "sent",
            "details": "Mock DTCC message sent successfully",
        })
    except Exception as e:
        dtcc_data["status"] = "failed"
        dtcc_data.setdefault("history", []).append({
            "timestamp": utc_now_iso(),
            "event": "failed",
            "details": str(e),
        })
        logger.exception(f"Error sending DTCC message {dtcc_id}: {e}")

@app.route("/trades/fpml", methods=["POST"])
@validate_request(Fpml_trade_request)
async def post_fpml_trade(data: Fpml_trade_request):
    try:
        if not await validate_fpml(data.fpmlMessage, data.signature):
            return jsonify({"message": "FpML validation failed"}), 400
        if not await verify_message_source():
            return jsonify({"message": "Message source authentication failed"}), 401
        trade_data = await parse_fpml(data.fpmlMessage)
        trade_data["status"] = "draft"
        trade_data["createdAt"] = utc_now_iso()
        trade_id_resp = await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model="trade",
            entity_version=ENTITY_VERSION,
            entity=trade_data
        )
        return jsonify({
            "tradeId": str(trade_id_resp),
            "status": trade_data["status"],
            "message": "Trade received and processed",
        })
    except Exception as e:
        logger.exception(e)
        return jsonify({"message": "Internal server error"}), 500

@validate_querystring(Legal_entity_query)
@app.route("/legal-entities", methods=["GET"])
async def get_legal_entities():
    try:
        lei = request.args.get("lei")
        name = request.args.get("name")
        jurisdiction = request.args.get("jurisdiction")
        if not any([lei, name, jurisdiction]):
            items = await entity_service.get_items(
                token=cyoda_auth_service,
                entity_model="legal_entity",
                entity_version=ENTITY_VERSION,
            )
        else:
            conditions = []
            if lei:
                conditions.append({
                    "jsonPath": "lei",
                    "operatorType": "EQUALS",
                    "value": lei,
                    "type": "simple"
                })
            if name:
                conditions.append({
                    "jsonPath": "name",
                    "operatorType": "ICONTAINS",
                    "value": name,
                    "type": "simple"
                })
            if jurisdiction:
                conditions.append({
                    "jsonPath": "jurisdiction",
                    "operatorType": "EQUALS",
                    "value": jurisdiction,
                    "type": "simple"
                })
            condition = {
                "cyoda": {
                    "type": "group",
                    "operator": "AND",
                    "conditions": conditions
                }
            }
            items = await entity_service.get_items_by_condition(
                token=cyoda_auth_service,
                entity_model="legal_entity",
                entity_version=ENTITY_VERSION,
                condition=condition
            )
        return jsonify(items)
    except Exception as e:
        logger.exception(e)
        return jsonify({"message": "Internal server error"}), 500

@app.route("/legal-entities", methods=["POST"])
@validate_request(Legal_entity_request)
async def post_legal_entity(data: Legal_entity_request):
    try:
        entity_data = {
            "lei": data.lei,
            "name": data.name,
            "jurisdiction": data.jurisdiction,
            "status": data.status,
        }
        existing = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model="legal_entity",
            entity_version=ENTITY_VERSION,
            technical_id=data.lei
        )
        if existing:
            await entity_service.update_item(
                token=cyoda_auth_service,
                entity_model="legal_entity",
                entity_version=ENTITY_VERSION,
                entity=entity_data,
                technical_id=data.lei,
                meta={}
            )
        else:
            await entity_service.add_item(
                token=cyoda_auth_service,
                entity_model="legal_entity",
                entity_version=ENTITY_VERSION,
                entity=entity_data
            )
        return jsonify({"lei": data.lei, "message": "Legal entity added or updated successfully"})
    except Exception as e:
        logger.exception(e)
        return jsonify({"message": "Internal server error"}), 500

@app.route("/dtcc/messages", methods=["POST"])
@validate_request(Dtcc_message_request)
async def post_dtcc_message(data: Dtcc_message_request):
    try:
        trade_item = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model="trade",
            entity_version=ENTITY_VERSION,
            technical_id=data.tradeId
        )
        if not trade_item:
            return jsonify({"message": f"Unknown tradeId {data.tradeId}"}), 400
        if data.messageType not in {"new", "modify", "cancel"}:
            return jsonify({"message": "Invalid messageType"}), 400
        dtcc_id = str(uuid.uuid4())
        dtcc_data = {
            "dtccMessageId": dtcc_id,
            "tradeId": data.tradeId,
            "messageType": data.messageType,
            "history": [],
        }
        await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model="dtcc_message",
            entity_version=ENTITY_VERSION,
            entity=dtcc_data
        )
        return jsonify({
            "dtccMessageId": dtcc_id,
            "status": "readyToSend",
            "message": "DTCC message generated and sent",
        })
    except Exception as e:
        logger.exception(e)
        return jsonify({"message": "Internal server error"}), 500

@app.route("/dtcc/messages/<dtcc_id>/resend", methods=["POST"])
async def post_dtcc_message_resend(dtcc_id: str):
    try:
        msg = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model="dtcc_message",
            entity_version=ENTITY_VERSION,
            technical_id=dtcc_id
        )
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
        await entity_service.update_item(
            token=cyoda_auth_service,
            entity_model="dtcc_message",
            entity_version=ENTITY_VERSION,
            entity=msg,
            technical_id=dtcc_id,
            meta={}
        )
        # Fire-and-forget send simulation on resend (allowed here because update endpoint)
        async def resend_send_simulation(message_id: str):
            try:
                await asyncio.sleep(1)
                msg_inner = await entity_service.get_item(
                    token=cyoda_auth_service,
                    entity_model="dtcc_message",
                    entity_version=ENTITY_VERSION,
                    technical_id=message_id
                )
                if not msg_inner:
                    return
                msg_inner["status"] = "sent"
                msg_inner["sentAt"] = utc_now_iso()
                msg_inner.setdefault("history", []).append({
                    "timestamp": utc_now_iso(),
                    "event": "sent",
                    "details": "Mock DTCC message resent successfully",
                })
                await entity_service.update_item(
                    token=cyoda_auth_service,
                    entity_model="dtcc_message",
                    entity_version=ENTITY_VERSION,
                    entity=msg_inner,
                    technical_id=message_id,
                    meta={}
                )
                logger.info(f"DTCC message {message_id} resent successfully")
            except Exception as e:
                logger.exception(f"Error resending DTCC message {message_id}: {e}")
        asyncio.create_task(resend_send_simulation(dtcc_id))
        return jsonify({
            "dtccMessageId": dtcc_id,
            "status": "readyToSend",
            "message": "Resend triggered",
        })
    except Exception as e:
        logger.exception(e)
        return jsonify({"message": "Internal server error"}), 500

@app.route("/dtcc/messages/<dtcc_id>", methods=["GET"])
async def get_dtcc_message(dtcc_id: str):
    try:
        msg = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model="dtcc_message",
            entity_version=ENTITY_VERSION,
            technical_id=dtcc_id
        )
        if not msg:
            return jsonify({"message": "DTCC message not found"}), 404
        return jsonify(msg)
    except Exception as e:
        logger.exception(e)
        return jsonify({"message": "Internal server error"}), 500

if __name__ == "__main__":
    import sys
    logging.basicConfig(
        stream=sys.stdout,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
        level=logging.INFO,
    )
    app.run(use_reloader=False, debug=True, host="0.0.0.0", port=8000, threaded=True)
