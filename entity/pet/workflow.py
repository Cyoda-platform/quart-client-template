async def start_brushing(entity: dict):
    entity["status"] = "Starting brushing process"
    entity["workflowProcessed"] = True

async def prepare_brush(entity: dict):
    entity["brush_ready"] = True
    entity["status"] = "Brush prepared"
    entity["workflowProcessed"] = True

async def handle_brush_not_ready(entity: dict):
    entity["brush_ready"] = False
    entity["status"] = "Brush not ready, returning to start"
    entity["workflowProcessed"] = True

async def brush_pet(entity: dict):
    entity["brushing"] = True
    entity["status"] = "Brushing the pet"
    entity["workflowProcessed"] = True

async def handle_brushing_failed(entity: dict):
    entity["brushing"] = False
    entity["status"] = "Brushing failed, handling issue"
    entity["workflowProcessed"] = True

async def check_pet_reaction(entity: dict):
    entity["status"] = "Checking pet reaction"
    entity["workflowProcessed"] = True

async def is_pet_happy(entity: dict):
    # Example condition check
    happy = entity.get("pet_mood", "") == "happy"
    return happy

async def is_pet_unhappy(entity: dict):
    # Example condition check
    unhappy = entity.get("pet_mood", "") == "unhappy"
    return unhappy

async def soothe_pet(entity: dict):
    entity["status"] = "Soothing the pet to retry brushing"
    entity["workflowProcessed"] = True

async def abort_brushing(entity: dict):
    entity["status"] = "Aborting brushing process"
    entity["workflowProcessed"] = True

async def fix_brushing_issue(entity: dict):
    entity["status"] = "Fixing brushing issue"
    entity["workflowProcessed"] = True

async def finish_brushing(entity: dict):
    entity["status"] = "Brushing process finished"
    entity["workflowProcessed"] = True