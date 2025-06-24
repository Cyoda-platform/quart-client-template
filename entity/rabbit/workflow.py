async def start_process(entity: dict):
    entity["status"] = "started"
    entity["workflowProcessed"] = False

async def process_data(entity: dict):
    # Example processing: brush rabbit entity
    if "rabbit" in entity:
        entity["rabbit"]["brushed"] = True
    entity["status"] = "processed"
    entity["workflowProcessed"] = True

async def handle_error(entity: dict):
    entity["status"] = "error"
    entity["errorHandled"] = True

async def approve_request(entity: dict):
    entity["status"] = "approved"
    entity["approvedBy"] = "system"

async def reject_request(entity: dict):
    entity["status"] = "rejected"
    entity["rejectedBy"] = "system"

async def retry_process(entity: dict):
    entity["status"] = "retrying"
    entity["retryCount"] = entity.get("retryCount", 0) + 1

async def abort_workflow(entity: dict):
    entity["status"] = "aborted"
    entity["workflowProcessed"] = False

async def finalize_workflow(entity: dict):
    entity["status"] = "completed"
    entity["workflowProcessed"] = True