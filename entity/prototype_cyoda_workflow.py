from dataclasses import dataclass
import asyncio
import logging
import uuid
from datetime import datetime
from typing import Dict, List, Optional

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

@dataclass
class Fpml_message_request:
    payload: str

@dataclass
class Legal_entity_record:
    lei: str
    legalName: str
    address: str
    countryCode: str

@dataclass
class Legal_entity_upload:
    entities: List[Legal_entity_record]

@dataclass
class Trade_status_request:
    newStatus: str
    eventDetails: Optional[dict] = None

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
        except Exception:
            logger.exception("FpML schema validation failed")
            return False

async def transmit_dtcc_message(payload: dict) -> bool:
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(DTCC_TRANSMISSION_API, json=payload, timeout=10)
            return resp.status_code == 200
        except Exception:
            logger.exception("DTCC message transmission failed")
            return False

# Workflow for fpml_message
async def process_fpml_message(entity):
    try:
        # Validate payload XML
        valid = await validate_fpml_xml(entity["payload"])
        processing_log = entity.get("processingLog", [])
        if not valid:
            entity["status"] = "ERROR"
            processing_log.append({"timestamp": now_iso(), "event": "Validation failed"})
            entity["processingLog"] = processing_log
            return entity

        # Get all trades
        trades_list = await entity_service.get_items(
            token=cyoda_auth_service,
            entity_model="trade",
            entity_version=ENTITY_VERSION,
        )

        matched_trade = None
        for trade in trades_list:
            if trade.get("tradeId") and trade["tradeId"] in entity["payload"]:
                matched_trade = trade
                break

        if matched_trade is None:
            entity["status"] = "UNMATCHED"
            processing_log.append({"timestamp": now_iso(), "event": "No matching trade"})
        else:
            entity["status"] = "MATCHED"
            processing_log.append({"timestamp": now_iso(), "event": f"Matched {matched_trade['id']}"})

        entity["status"] = "VALIDATED"
        processing_log.append({"timestamp": now_iso(), "event": "Validated"})
        entity["processingLog"] = processing_log

        # Create or update trade accordingly
        if matched_trade is None:
            trade_id = str(uuid.uuid4())
            new_trade = {
                "id": trade_id,
                "tradeId": f"trade-{trade_id[:8]}",
                "productType": "Unknown",
                "party1LEI": "LEI0000001",
                "party2LEI": "LEI0000002",
                "tradeDetails": {},
                "status": "UNCONFIRMED",
                "originalFpMLMessageId": entity.get("id"),  # id not set yet, will be None here
                "events": [],
                "latestVersion": 1,
                "processingLog": [{"timestamp": now_iso(), "event": "Trade created"}],
            }
            await entity_service.add_item(
                token=cyoda_auth_service,
                entity_model="trade",
                entity_version=ENTITY_VERSION,
                entity=new_trade,
                workflow=process_trade
            )
        else:
            matched_trade["latestVersion"] += 1
            trade_processing_log = matched_trade.get("processingLog", [])
            trade_processing_log.append({"timestamp": now_iso(), "event": "Trade updated"})
            matched_trade["processingLog"] = trade_processing_log
            await entity_service.update_item(
                token=cyoda_auth_service,
                entity_model="trade",
                entity_version=ENTITY_VERSION,
                entity=matched_trade,
                technical_id=matched_trade["id"],
                meta={}
            )
    except Exception:
        logger.exception("Exception in process_fpml_message workflow")
        entity["status"] = "ERROR"
        processing_log = entity.get("processingLog", [])
        processing_log.append({"timestamp": now_iso(), "event": "Exception in workflow"})
        entity["processingLog"] = processing_log
    return entity

# Workflow for trade
async def process_trade(entity):
    try:
        processing_log = entity.get("processingLog", [])

        if entity.get("status") in (None, "UNCONFIRMED"):
            entity["status"] = "CONFIRMED"
            processing_log.append({"timestamp": now_iso(), "event": "Confirmed"})

        party1_lei = entity.get("party1LEI")
        party2_lei = entity.get("party2LEI")

        legal_entity1 = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model="legal_entity",
            entity_version=ENTITY_VERSION,
            technical_id=party1_lei
        )
        legal_entity2 = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model="legal_entity",
            entity_version=ENTITY_VERSION,
            technical_id=party2_lei
        )

        if not legal_entity1 or not legal_entity2:
            entity["status"] = "ERROR"
            processing_log.append({"timestamp": now_iso(), "event": "Missing LEI data"})
            entity["processingLog"] = processing_log
            return entity

        processing_log.append({"timestamp": now_iso(), "event": "Enriched"})
        entity["status"] = "VALIDATED"
        processing_log.append({"timestamp": now_iso(), "event": "Validated trade"})
        entity["processingLog"] = processing_log

        dtcc_id = str(uuid.uuid4())
        dtcc_msg = {
            "id": dtcc_id,
            "type": "New Trade",
            "payload": {"tradeId": entity["tradeId"], "details": entity["tradeDetails"]},
            "status": "PENDING_TRANSMISSION",
            "creationTimestamp": now_iso(),
            "transmissionTimestamp": None,
            "acknowledgementTimestamp": None,
            "relatedTradeId": entity["id"],
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

            processing_log.append({"timestamp": now_iso(), "event": "DTCC ack"})
            entity["processingLog"] = processing_log
        else:
            dtcc_msg["status"] = "ERROR"
            dtcc_msg["processingLog"].append({"timestamp": now_iso(), "event": "Transmission error"})

            entity["status"] = "ERROR"
            processing_log.append({"timestamp": now_iso(), "event": "DTCC failure"})
            entity["processingLog"] = processing_log
    except Exception:
        logger.exception("Exception in process_trade workflow")
        entity["status"] = "ERROR"
        processing_log = entity.get("processingLog", [])
        processing_log.append({"timestamp": now_iso(), "event": "Exception in trade workflow"})
        entity["processingLog"] = processing_log
    return entity

# Workflow for legal_entity
async def process_legal_entity(entity):
    try:
        entity["status"] = "ACTIVE"
        entity["lastUpdated"] = now_iso()
    except Exception:
        logger.exception("Exception in process_legal_entity workflow")
        entity["status"] = "ERROR"
    return entity

@app.route("/api/fpml-messages", methods=["POST"])
@validate_request(Fpml_message_request)
async def receive_fpml_message(data: Fpml_message_request):
    message = {
        "payload": data.payload,
        "status": "PENDING",
        "receivedTimestamp": now_iso(),
        "processingLog": [{"timestamp": now_iso(), "event": "Received"}],
    }
    try:
        message_id = await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model="fpml_message",
            entity_version=ENTITY_VERSION,
            entity=message,
            workflow=process_fpml_message
        )
        return jsonify({"messageId": message_id, "status": "PENDING", "acknowledgement": "Received"}), 202
    except Exception:
        logger.exception("Failed to add fpml_message")
        return jsonify({"error": "Failed to add fpml_message"}), 500

@app.route("/api/legal-entities", methods=["POST"])
@validate_request(Legal_entity_upload)
async def upload_legal_entities(data: Legal_entity_upload):
    async def add_legal_entity_entity(rec: Legal_entity_record):
        entity = {
            "lei": rec.lei,
            "legalName": rec.legalName,
            "address": rec.address,
            "countryCode": rec.countryCode,
        }
        try:
            existing = await entity_service.get_item(
                token=cyoda_auth_service,
                entity_model="legal_entity",
                entity_version=ENTITY_VERSION,
                technical_id=rec.lei
            )
            if existing:
                entity["status"] = existing.get("status", "ACTIVE")
                entity["lastUpdated"] = now_iso()
                await entity_service.update_item(
                    token=cyoda_auth_service,
                    entity_model="legal_entity",
                    entity_version=ENTITY_VERSION,
                    entity=entity,
                    technical_id=rec.lei,
                    meta={}
                )
            else:
                await entity_service.add_item(
                    token=cyoda_auth_service,
                    entity_model="legal_entity",
                    entity_version=ENTITY_VERSION,
                    entity=entity,
                    workflow=process_legal_entity
                )
        except Exception:
            logger.exception(f"Failed to process legal_entity {rec.lei}")

    asyncio.create_task(asyncio.gather(*(add_legal_entity_entity(rec) for rec in data.entities)))
    return jsonify({"uploadedCount": len(data.entities), "status": "PENDING_UPLOAD"}), 200

@app.route("/api/trades/<trade_id>/status", methods=["POST"])
@validate_request(Trade_status_request)
async def update_trade_status(data: Trade_status_request, trade_id):
    try:
        trade = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model="trade",
            entity_version=ENTITY_VERSION,
            technical_id=trade_id
        )
        if not trade:
            return jsonify({"error": "Trade not found"}), 404
        trade["status"] = data.newStatus
        processing_log = trade.get("processingLog", [])
        processing_log.append({
            "timestamp": now_iso(),
            "event": f"Status updated: {data.newStatus}",
            "details": data.eventDetails or {}
        })
        trade["processingLog"] = processing_log
        await entity_service.update_item(
            token=cyoda_auth_service,
            entity_model="trade",
            entity_version=ENTITY_VERSION,
            entity=trade,
            technical_id=trade_id,
            meta={}
        )
        return jsonify({"tradeId": trade_id, "updatedStatus": data.newStatus}), 200
    except Exception:
        logger.exception("Failed to update trade status")
        return jsonify({"error": "Failed to update trade status"}), 500

@app.route("/api/trades/<trade_id>", methods=["GET"])
async def get_trade(trade_id):
    try:
        trade = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model="trade",
            entity_version=ENTITY_VERSION,
            technical_id=trade_id
        )
        if not trade:
            return jsonify({"error": "Trade not found"}), 404
        return jsonify(trade), 200
    except Exception:
        logger.exception("Failed to get trade")
        return jsonify({"error": "Failed to get trade"}), 500

@app.route("/api/dtcc-messages/<dtcc_id>", methods=["GET"])
async def get_dtcc_message(dtcc_id):
    msg = dtcc_messages.get(dtcc_id)
    if not msg:
        return jsonify({"error": "DTCCMessage not found"}), 404
    return jsonify(msg), 200

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)