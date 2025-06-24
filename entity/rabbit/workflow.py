async def start_brushing(entity: dict):
    entity["status"] = "started brushing"
    entity["workflowProcessed"] = True

async def pick_brush(entity: dict):
    entity["brush_picked"] = True
    entity["workflowProcessed"] = True

async def move_to_rabbit(entity: dict):
    entity["position"] = "near_rabbit"
    entity["workflowProcessed"] = True

async def is_rabbit_calmed(entity: dict):
    mood = entity.get("mood", "agitated")
    return mood == "calm"

async def wait_before_retry(entity: dict):
    entity["waited"] = True
    entity["workflowProcessed"] = True

async def brush_rabbit(entity: dict):
    if entity.get("brush_picked") and entity.get("position") == "near_rabbit":
        entity["brushed"] = True
    entity["workflowProcessed"] = True

async def clean_brush(entity: dict):
    entity["brush_cleaned"] = True
    entity["workflowProcessed"] = True