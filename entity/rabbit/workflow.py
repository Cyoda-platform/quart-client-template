async def start_process(entity: dict):
    entity["status"] = "started"
    entity["workflowProcessed"] = False

async def process_state_01_to_02(entity: dict):
    entity["step"] = "processing from state_01 to state_02"
    entity["workflowProcessed"] = False

async def check_condition(entity: dict):
    # Example condition check, user can customize as needed
    entity["condition_met"] = entity.get("brushRabbit", False) is True
    return entity["condition_met"]

async def finalize_process(entity: dict):
    if entity.get("condition_met"):
        entity["status"] = "brush_rabbit_completed"
    else:
        entity["status"] = "brush_rabbit_skipped"
    entity["workflowProcessed"] = True