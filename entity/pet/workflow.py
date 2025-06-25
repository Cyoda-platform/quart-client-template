async def start_brushing(entity: dict):
    entity["status"] = "Brushing started"
    entity["workflowProcessed"] = True

async def pick_up_brush(entity: dict):
    entity["brush"] = "picked up"
    entity["workflowProcessed"] = True

async def brush_body(entity: dict):
    if "brushed_parts" not in entity:
        entity["brushed_parts"] = []
    entity["brushed_parts"].append("body")
    entity["workflowProcessed"] = True

async def check_pet_reaction(entity: dict):
    # Placeholder logic, should be replaced with actual pet reaction check
    if entity.get("pet_mood", "calm") in ["agitated", "scared"]:
        entity["pet_reaction"] = "uncomfortable"
    else:
        entity["pet_reaction"] = "comfortable"
    entity["workflowProcessed"] = True

async def is_pet_uncomfortable(entity: dict) -> bool:
    return entity.get("pet_reaction") == "uncomfortable"

async def is_pet_comfortable(entity: dict) -> bool:
    return entity.get("pet_reaction") == "comfortable"

async def soothe_pet(entity: dict):
    entity["soothed"] = True
    entity["workflowProcessed"] = True

async def stop_brushing(entity: dict):
    entity["status"] = "Brushing stopped due to pet discomfort"
    entity["workflowProcessed"] = True

async def put_away_brush(entity: dict):
    entity["brush"] = "put away"
    entity["status"] = "Brushing finished"
    entity["workflowProcessed"] = True