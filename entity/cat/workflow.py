async def process_start(entity: dict):
    entity["status"] = "brushing_started"
    entity["workflowProcessed"] = False

async def process_brush_cat(entity: dict):
    entity["cat_brushed"] = True
    entity["workflowProcessed"] = True