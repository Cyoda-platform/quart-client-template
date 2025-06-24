async def process_start(entity: dict):
    entity["status"] = "washing_started"
    entity["workflowProcessed"] = False

async def process_wash_cat(entity: dict):
    entity["cat_washed"] = True
    entity["workflowProcessed"] = True