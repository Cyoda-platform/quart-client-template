Certainly! I've updated the `entity_service.add_item` calls to include the new `workflow` argument as required. The workflow function is implemented with the prefix `process_` followed by the underscore-lowercase entity name, as instructed.

Specifically:

- Added `async def process_fpml_message_workflow(entity):` for `fpml_message`.
- Added `async def process_trade_workflow(entity):` for `trade`.
- Added `async def process_legal_entity_workflow(entity):` for `legal_entity`.

These workflow functions currently just return the entity unchanged (no modifications) but can be extended as needed.  
The `add_item` calls now pass the corresponding workflow function.

Here is the complete updated code for `entity/prototype_cyoda.py`:

```python
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

# Data classes for request validation
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
    # Workaround: wrap list to allow validate_request on POST due to quart-schema issue
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

# Workflow functions for add_item
async def process_fpml_message_workflow(entity):
    # This function receives the entity before persistence. Modify as needed.
    # For example, you can initialize or modify entity fields here.
    return entity

async def process_trade_workflow(entity):
    # Modify trade entity before persistence if needed.
    return entity

async def process_legal_entity_workflow(entity):
    # Modify legal_entity entity before persistence if needed.
    return entity

async def process_fpml_message(message_id: str):
    try:
        msg = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model="fpml_message",
            entity_version=ENTITY_VERSION,
            technical_id=message_id
        )
        if not msg:
            logger.error(f"Fpml_message {message_id} not found")
            return

        valid = await validate_fpml_xml(msg["payload"])
        processing_log = msg.get("processingLog", [])
        if not valid:
            msg["status"] = "ERROR"
            processing_log.append({"timestamp": now_iso(), "event": "Validation failed"})
            msg["processingLog"] = processing_log
            await entity_service.update_item(
                token=cyoda_auth_service,
                entity_model="fpml_message",
                entity_version=ENTITY_VERSION,
                entity=msg,
                technical_id=message_id,
                meta={}
            )
            return

        # Retrieve trades with condition "status" != "ERROR" or all trades (no condition here)
        trades_list = await entity_service.get_items(
            token=cyoda_auth_service,
            entity_model="trade",
            entity_version=ENTITY_VERSION,
        )

        matched_trade_id = None
        for trade in trades_list:
            if trade["tradeId"] in msg["payload"]:
                matched_trade_id = trade["id"]
                break

        if matched_trade_id is None:
            msg["status"] = "UNMATCHED"
            processing_log.append({"timestamp": now_iso(), "event": "No matching trade"})
        else:
            msg["status"] = "MATCHED"
            processing_log.append({"timestamp": now_iso(), "event": f"Matched {matched_trade_id}"})

        msg["status"] = "VALIDATED"
        processing_log.append({"timestamp": now_iso(), "event": "Validated"})
        msg["processingLog"] = processing_log
        await entity_service.update_item(
            token=cyoda_auth_service,
            entity_model="fpml_message",
            entity_version=ENTITY_VERSION,
            entity=msg,
            technical_id=message_id,
            meta={}
        )

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
            await entity_service.add_item(
                token=cyoda_auth_service,
                entity_model="trade",
                entity_version=ENTITY_VERSION,
                entity=trade,
                workflow=process_trade_workflow
            )
        else:
            trade = await entity_service.get_item(
                token=cyoda_auth_service,
                entity_model="trade",
                entity_version=ENTITY_VERSION,
                technical_id=matched_trade_id
            )
            trade["latestVersion"] += 1
            trade_processing_log = trade.get("processingLog", [])
            trade_processing_log.append({"timestamp": now_iso(), "event": "Trade updated"})
            trade["processingLog"] = trade_processing_log
            await entity_service.update_item(
                token=cyoda_auth_service,
                entity_model="trade",
                entity_version=ENTITY_VERSION,
                entity=trade,
                technical_id=matched_trade_id,
                meta={}
            )

        # Refresh trade after update or creation
        if matched_trade_id is None:
            trade = await entity_service.get_item(
                token=cyoda_auth_service,
                entity_model="trade",
                entity_version=ENTITY_VERSION,
                technical_id=trade_id
            )
        else:
            trade = await entity_service.get_item(
                token=cyoda_auth_service,
                entity_model="trade",
                entity_version=ENTITY_VERSION,
                technical_id=matched_trade_id
            )

        trade_processing_log = trade.get("processingLog", [])

        trade["status"] = "CONFIRMED"
        trade_processing_log.append({"timestamp": now_iso(), "event": "Confirmed"})

        # Check legal entities existence
        party1_lei = trade["party1LEI"]
        party2_lei = trade["party2LEI"]
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
        if legal_entity1 and legal_entity2:
            trade_processing_log.append({"timestamp": now_iso(), "event": "Enriched"})
        else:
            trade["status"] = "ERROR"
            trade_processing_log.append({"timestamp": now_iso(), "event": "Missing LEI data"})
            trade["processingLog"] = trade_processing_log
            await entity_service.update_item(
                token=cyoda_auth_service,
                entity_model="trade",
                entity_version=ENTITY_VERSION,
                entity=trade,
                technical_id=trade["id"],
                meta={}
            )
            return

        trade["status"] = "VALIDATED"
        trade_processing_log.append({"timestamp": now_iso(), "event": "Validated trade"})
        trade["processingLog"] = trade_processing_log
        await entity_service.update_item(
            token=cyoda_auth_service,
            entity_model="trade",
            entity_version=ENTITY_VERSION,
            entity=trade,
            technical_id=trade["id"],
            meta={}
        )

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
            trade_processing_log.append({"timestamp": now_iso(), "event": "DTCC ack"})
            trade["processingLog"] = trade_processing_log
            await entity_service.update_item(
                token=cyoda_auth_service,
                entity_model="trade",
                entity_version=ENTITY_VERSION,
                entity=trade,
                technical_id=trade["id"],
                meta={}
            )
        else:
            dtcc_msg["status"] = "ERROR"
            dtcc_msg["processingLog"].append({"timestamp": now_iso(), "event": "Transmission error"})
            trade["status"] = "ERROR"
            trade_processing_log.append({"timestamp": now_iso(), "event": "DTCC failure"})
            trade["processingLog"] = trade_processing_log
            await entity_service.update_item(
                token=cyoda_auth_service,
                entity_model="trade",
                entity_version=ENTITY_VERSION,
                entity=trade,
                technical_id=trade["id"],
                meta={}
            )
    except Exception as e:
        try:
            msg = await entity_service.get_item(
                token=cyoda_auth_service,
                entity_model="fpml_message",
                entity_version=ENTITY_VERSION,
                technical_id=message_id
            )
            if msg:
                msg["status"] = "ERROR"
                processing_log = msg.get("processingLog", [])
                processing_log.append({"timestamp": now_iso(), "event": "Exception"})
                msg["processingLog"] = processing_log
                await entity_service.update_item(
                    token=cyoda_auth_service,
                    entity_model="fpml_message",
                    entity_version=ENTITY_VERSION,
                    entity=msg,
                    technical_id=message_id,
                    meta={}
                )
        except Exception as inner_e:
            logger.exception(inner_e)
        logger.exception(e)

async def process_legal_entity_upload(records: List[Legal_entity_record]):
    for rec in records:
        lei = rec.lei
        if not lei:
            continue
        entity = {
            "lei": lei,
            "legalName": rec.legalName,
            "address": rec.address,
            "countryCode": rec.countryCode,
            "status": "ACTIVE",
            "lastUpdated": now_iso(),
        }
        try:
            # try update first
            existing = await entity_service.get_item(
                token=cyoda_auth_service,
                entity_model="legal_entity",
                entity_version=ENTITY_VERSION,
                technical_id=lei
            )
            if existing:
                await entity_service.update_item(
                    token=cyoda_auth_service,
                    entity_model="legal_entity",
                    entity_version=ENTITY_VERSION,
                    entity=entity,
                    technical_id=lei,
                    meta={}
                )
            else:
                await entity_service.add_item(
                    token=cyoda_auth_service,
                    entity_model="legal_entity",
                    entity_version=ENTITY_VERSION,
                    entity=entity,
                    workflow=process_legal_entity_workflow
                )
        except Exception as e:
            logger.exception(f"Failed to process legal_entity {lei}: {e}")

@app.route("/api/fpml-messages", methods=["POST"])
@validate_request(Fpml_message_request)  # Workaround: validation last for POST due to defect
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
            workflow=process_fpml_message_workflow
        )
        asyncio.create_task(process_fpml_message(message_id))
        return jsonify({"messageId": message_id, "status": "PENDING", "acknowledgement": "Received"}), 202
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to add fpml_message"}), 500

@app.route("/api/legal-entities", methods=["POST"])
@validate_request(Legal_entity_upload)  # Workaround: validation last for POST due to defect
async def upload_legal_entities(data: Legal_entity_upload):
    asyncio.create_task(process_legal_entity_upload(data.entities))
    return jsonify({"uploadedCount": len(data.entities), "status": "PENDING_UPLOAD"}), 200

@app.route("/api/trades/<trade_id>/status", methods=["POST"])
@validate_request(Trade_status_request)  # Workaround: validation last for POST due to defect
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
    except Exception as e:
        logger.exception(e)
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
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to get trade"}), 500

@app.route("/api/dtcc-messages/<dtcc_id>", methods=["GET"])
async def get_dtcc_message(dtcc_id):
    msg = dtcc_messages.get(dtcc_id)
    if not msg:
        return jsonify({"error": "DTCCMessage not found"}), 404
    return jsonify(msg), 200

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
```

---

### Summary of changes:
- Added three async workflow functions:
  - `process_fpml_message_workflow`
  - `process_trade_workflow`
  - `process_legal_entity_workflow`
- Passed `workflow=process_<entity_name>_workflow` argument to each `add_item` call.
- No changes to other logic.

Let me know if you want the workflows to perform specific transformations or validations!