import asyncio
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

def now_iso():
    from datetime import datetime
    return datetime.utcnow().isoformat() + "Z"

async def process_payment(entity: Dict[str, Any]) -> Dict[str, Any]:
    # Workflow orchestration only
    entity.setdefault("status", "queued")
    entity.setdefault("requestedAt", now_iso())

    payment_id = entity.get("technicalId") or entity.get("paymentId")
    if not payment_id:
        return entity

    asyncio.create_task(process_payment_task(entity, payment_id))
    return entity

async def process_payment_task(entity: Dict[str, Any], payment_id: str):
    try:
        await asyncio.sleep(2)
        # Business logic: simulate payment processing
        entity["status"] = "processed"
        entity["processedDate"] = now_iso()
        logger.info(f"Payment processed: {payment_id}")
    except Exception as e:
        entity["status"] = "error"
        logger.exception(e)