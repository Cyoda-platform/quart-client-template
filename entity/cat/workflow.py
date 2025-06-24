async def process_start(entity: dict):
    entity["status"] = "started"
    entity["workflowProcessed"] = False

async def process_process_cat(entity: dict):
    entity["cat_processed"] = True
    entity["workflowProcessed"] = True