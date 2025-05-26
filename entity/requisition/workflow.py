from datetime import datetime
from typing import Dict, Any

def now_iso():
    return datetime.utcnow().isoformat() + "Z"

async def process_submit(entity: Dict[str, Any]) -> None:
    entity['status'] = 'submitted'
    entity['submittedAt'] = now_iso()
    if 'approvalHistory' not in entity:
        entity['approvalHistory'] = []

async def process_approve(entity: Dict[str, Any]) -> None:
    entity['status'] = 'approved'
    entity['approvalHistory'].append({
        "task": "approval",
        "user": entity.get("currentApprover", "system"),
        "timestamp": now_iso(),
        "action": "approved"
    })

async def process_reject(entity: Dict[str, Any]) -> None:
    entity['status'] = 'rejected'
    entity['approvalHistory'].append({
        "task": "approval",
        "user": entity.get("currentApprover", "system"),
        "timestamp": now_iso(),
        "action": "rejected"
    })

async def process_requisition(entity: Dict[str, Any]) -> Dict[str, Any]:
    # Workflow orchestration only
    if 'status' not in entity or entity['status'] == 'pending':
        await process_submit(entity)
    elif entity['status'] == 'submitted' and entity.get('action') == 'approve':
        await process_approve(entity)
    elif entity['status'] == 'submitted' and entity.get('action') == 'reject':
        await process_reject(entity)
    return entity