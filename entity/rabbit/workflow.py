async def start_brushing(entity: dict):
    entity["status"] = "brushing_started"
    entity["workflowProcessed"] = True

async def approach_rabbit(entity: dict):
    entity["status"] = "approaching_rabbit"
    entity["workflowProcessed"] = True

async def is_rabbit_calm(entity: dict) -> bool:
    return entity.get("mood") == "calm"

async def is_rabbit_agitated(entity: dict) -> bool:
    return entity.get("mood") == "agitated"

async def calm_rabbit(entity: dict):
    entity["status"] = "calming_rabbit"
    # Example: apply calming procedure
    entity["mood"] = "calm"
    entity["workflowProcessed"] = True

async def start_brush(entity: dict):
    entity["status"] = "brushing_started"
    entity["workflowProcessed"] = True

async def brush_rabbit(entity: dict):
    entity["status"] = "brushing_in_progress"
    # Example: simulate brushing action
    entity["brushed"] = True
    entity["workflowProcessed"] = True

async def handle_escape(entity: dict):
    entity["status"] = "rabbit_moved_away"
    entity["workflowProcessed"] = True

async def regain_rabbit(entity: dict):
    entity["status"] = "regaining_rabbit"
    # Example: reset mood to calm to allow brushing again
    entity["mood"] = "calm"
    entity["workflowProcessed"] = True

async def give_up_brushing(entity: dict):
    entity["status"] = "gave_up_brushing"
    entity["workflowProcessed"] = True