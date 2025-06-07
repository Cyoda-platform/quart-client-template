from datetime import datetime, timezone

def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


async def process_legal_entity(legal_entity_data: dict):
    # Workflow orchestration for legal entity: update timestamp
    legal_entity_data["updatedAt"] = utc_now_iso()


async def process_trade(trade_data: dict):
    # Workflow orchestration for trade lifecycle state transitions
    event_type = trade_data.get("eventType", "execution")
    current_state = trade_data.get("status", "draft")

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

    trade_data["status"] = next_state
    trade_data["lastUpdated"] = utc_now_iso()


async def process_dtcc_message(dtcc_message_data: dict):
    # Workflow orchestration for DTCC message sending status
    status = dtcc_message_data.get("status", "readyToSend")

    if status == "readyToSend":
        # Simulate sending success
        dtcc_message_data["status"] = "sent"
        dtcc_message_data["sentAt"] = utc_now_iso()
        dtcc_message_data.setdefault("history", []).append({
            "timestamp": utc_now_iso(),
            "event": "sent",
            "details": "Mock DTCC message sent successfully",
        })
    elif status == "failed":
        # Could add retry logic here if needed
        pass
    # else no state change for 'sent' or other states
