async def start_brushing(entity: dict):
    entity["status"] = "Brushing process started"
    entity["workflowProcessed"] = True

async def prepare_brush(entity: dict):
    entity["brush_prepared"] = True
    entity["workflowProcessed"] = True

async def approach_pet(entity: dict):
    entity["pet_approached"] = True
    entity["workflowProcessed"] = True

async def calm_pet_down(entity: dict):
    entity["pet_calm"] = True
    entity["workflowProcessed"] = True

async def abort_brushing(entity: dict):
    entity["status"] = "Brushing aborted"
    entity["workflowProcessed"] = True

async def start_brushing_pet(entity: dict):
    entity["brushing_started"] = True
    entity["workflowProcessed"] = True

async def brush_pet(entity: dict):
    if "brushing_started" in entity and entity["brushing_started"]:
        entity["brushing_in_progress"] = True
    entity["workflowProcessed"] = True

async def finish_brushing(entity: dict):
    entity["brushing_complete"] = True
    entity["workflowProcessed"] = True