import asyncio
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

def now_iso():
    from datetime import datetime
    return datetime.utcnow().isoformat() + "Z"

async def process_report(entity: Dict[str, Any]) -> Dict[str, Any]:
    # Workflow orchestration only
    entity.setdefault("status", "queued")
    entity.setdefault("createdDate", now_iso())
    entity.setdefault("downloadUrl", None)

    report_id = entity.get("technicalId") or entity.get("reportId")
    if not report_id:
        return entity

    asyncio.create_task(process_report_task(entity, report_id))
    return entity

async def process_report_task(entity: Dict[str, Any], report_id: str):
    try:
        await asyncio.sleep(1)
        # Business logic here: simulate report generation
        entity["status"] = "ready"
        entity["downloadUrl"] = f"https://mockreports.example.com/download/{report_id}"
        logger.info(f"Report ready: {report_id}")
    except Exception as e:
        entity["status"] = "error"
        logger.exception(e)