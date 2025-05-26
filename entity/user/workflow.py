from datetime import datetime
from typing import Dict, Any

def now_iso():
    return datetime.utcnow().isoformat() + "Z"

async def process_user(entity: Dict[str, Any]) -> Dict[str, Any]:
    # Workflow orchestration only
    if "createdAt" not in entity:
        await process_set_creation(entity)
    if entity.get("role") == "Finance Manager":
        await process_finance_manager(entity)
    if entity.get("workflowEvent") == "trigger_workflow":
        await process_workflow(entity)
    return entity

async def process_set_creation(entity: Dict[str, Any]):
    entity["createdAt"] = now_iso()

async def process_finance_manager(entity: Dict[str, Any]):
    # Business logic placeholder for Finance Manager role
    entity["financeManagerProcessed"] = True

async def process_workflow(entity: Dict[str, Any]):
    # Business logic placeholder for workflow trigger event
    entity["workflowStatus"] = "started"
    # Simulate workflow processing
    entity["workflowStatus"] = "completed"