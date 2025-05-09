async def process_start_happy_workflow(entity: dict):
    entity["status"] = "initiated"
    entity["startedAt"] = entity.get("requestedAt") or "unknown"
    entity["workflowProcessed"] = False

async def process_process_happy_message(entity: dict):
    message = entity.get("message", "No message provided")
    processed_message = message.upper()  # simple example processing
    entity["processedMessage"] = processed_message
    entity["workflowProcessed"] = True

async def process_complete_happy_workflow(entity: dict):
    entity["status"] = "completed"
    entity["completedAt"] = entity.get("completedAt") or "unknown"
    entity["workflowProcessed"] = True