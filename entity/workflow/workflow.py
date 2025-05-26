import asyncio
from datetime import datetime
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

def now_iso():
    return datetime.utcnow().isoformat() + "Z"

async def process_workflow(entity: Dict[str, Any]) -> Dict[str, Any]:
    entity.setdefault("state", "initialized")
    entity.setdefault("currentTask", None)
    entity.setdefault("history", [])
    entity.setdefault("startedAt", now_iso())

    workflow_id = entity.get("technicalId") or entity.get("workflowId")
    if not workflow_id:
        return entity

    # Workflow orchestration
    await process_workflow_task(entity)

    return entity

async def process_workflow_task(entity: Dict[str, Any]):
    try:
        await asyncio.sleep(1)  # simulate async processing
        entity["state"] = "completed"
        entity["currentTask"] = None
        entity.setdefault("history", []).append({
            "task": "initial",
            "user": "system",
            "timestamp": now_iso(),
            "action": "completed"
        })
        logger.info(f"Workflow {entity.get('technicalId') or entity.get('workflowId')} completed")
    except Exception as e:
        logger.exception(e)