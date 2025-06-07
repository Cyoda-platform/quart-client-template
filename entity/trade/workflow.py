from datetime import datetime, timezone
import logging
import uuid
import asyncio

logger = logging.getLogger(__name__)

def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

async def process_check_legal_entity(trade_data: dict):
    lei = trade_data.get("counterpartyLEI")
    if not await check_legal_entity_exists(lei):
        trade_data["status"] = "rejected"
        trade_data["rejectionReason"] = f"Unknown legal entity LEI: {lei}"

async def process_transition_state(trade_data: dict):
    event_type = trade_data.get("eventType", "execution")
    transition_trade_state(trade_data, event_type)

async def process_set_last_processed_at(trade_data: dict):
    trade_data["lastProcessedAt"] = utc_now_iso()

async def process_trade(trade_data: dict):
    try:
        await process_check_legal_entity(trade_data)
        if trade_data.get("status") != "rejected":
            await process_transition_state(trade_data)
        await process_set_last_processed_at(trade_data)
    except Exception as e:
        logger.exception(f"Error in process_trade workflow: {e}")