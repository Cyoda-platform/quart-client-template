async def process_start_activity(entity: dict):
    entity["activity_status"] = "started"
    entity["workflowProcessed"] = True

async def process_update_activity(entity: dict):
    entity["activity_status"] = "updated"
    entity["workflowProcessed"] = True

async def process_complete_activity(entity: dict):
    entity["activity_status"] = "completed"
    entity["workflowProcessed"] = True