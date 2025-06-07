import asyncio
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)
def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

async def process_validate_fpml(entity: dict):
    # TODO: Implement real FpML schema validation and signature verification
    if not entity.get("fpmlMessage") or not entity["fpmlMessage"].strip():
        entity["validationStatus"] = "failed"
    else:
        entity["validationStatus"] = "passed"

async def process_verify_message_source(entity: dict):
    # TODO: Implement real mTLS or signed payload verification
    entity["sourceVerified"] = True

async def process_parse_fpml(entity: dict):
    # TODO: Implement real FpML parsing extracting trade data
    # For prototype, simulate parsed data
    entity["tradeId"] = entity.get("tradeId") or "trade-" + utc_now_iso()
    entity["counterpartyLEI"] = "5493001KJTIIGC8Y1R12"
    entity["eventType"] = entity.get("eventType") or "tradeConfirmation"

async def process_check_legal_entity(entity: dict):
    # TODO: Replace with actual legal entity lookup
    lei = entity.get("counterpartyLEI")
    entity["legalEntityKnown"] = lei == "5493001KJTIIGC8Y1R12"

async def process_transition_trade_state(entity: dict):
    current_state = entity.get("status", "draft")
    event_type = entity.get("eventType", "execution")
    if event_type in ["execution", "newTrade"]:
        entity["status"] = "draft"
    elif event_type == "tradeConfirmation" and current_state == "draft":
        entity["status"] = "confirmed"
    elif event_type in ["amendment", "modification"] and current_state == "confirmed":
        entity["status"] = "amended"
    elif event_type in ["cancel", "termination"]:
        entity["status"] = "cancelled"
    elif event_type == "rejection" and current_state in ["draft", "confirmed"]:
        entity["status"] = "rejected"
    else:
        entity["status"] = current_state
    entity["lastUpdated"] = utc_now_iso()

async def process_trade(entity: dict):
    await process_validate_fpml(entity)
    if entity.get("validationStatus") == "failed":
        entity["status"] = "rejected"
        return
    await process_verify_message_source(entity)
    if not entity.get("sourceVerified"):
        entity["status"] = "rejected"
        return
    await process_parse_fpml(entity)
    await process_check_legal_entity(entity)
    if not entity.get("legalEntityKnown"):
        entity["status"] = "rejected"
        entity["rejectionReason"] = "Unknown legal entity LEI"
        return
    await process_transition_trade_state(entity)

async def process_send_dtcc(entity: dict):
    if "status" not in entity:
        entity["status"] = "readyToSend"
    if "createdAt" not in entity:
        entity["createdAt"] = utc_now_iso()
    try:
        await asyncio.sleep(1)
        entity["status"] = "sent"
        entity["sentAt"] = utc_now_iso()
        entity.setdefault("history", []).append({
            "timestamp": utc_now_iso(),
            "event": "sent",
            "details": "Mock DTCC message sent successfully",
        })
    except Exception as e:
        entity["status"] = "failed"
        entity.setdefault("history", []).append({
            "timestamp": utc_now_iso(),
            "event": "failed",
            "details": str(e),
        })
        logger.exception(f"Error sending DTCC message: {e}")

async def process_dtcc_message(entity: dict):
    # Workflow orchestration only - no business logic here
    if entity.get("status") in (None, "readyToSend", "failed"):
        await process_send_dtcc(entity)