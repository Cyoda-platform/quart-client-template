async def process_transition_to_state_01(entity: dict):
    entity["log"] = entity.get("log", []) + ["Started workflow: brushing rabbit"]
    entity["workflowProcessed"] = False

async def process_transition_to_state_02(entity: dict):
    entity["log"] = entity.get("log", []) + ["Preparing to brush rabbit"]
    entity["workflowProcessed"] = False

async def process_transition_with_condition_simple(entity: dict):
    entity["log"] = entity.get("log", []) + ["Checking if rabbit is ready to be brushed"]
    is_ready = entity.get("rabbit_ready", False)
    entity["condition_result"] = is_ready
    entity["workflowProcessed"] = False

async def process_transition_with_condition_simple_returns_bool(entity: dict) -> bool:
    return entity.get("rabbit_ready", False)

async def process_transition_with_condition_group(entity: dict):
    entity["log"] = entity.get("log", []) + ["Brushing rabbit started"]
    entity["brushed"] = True
    entity["workflowProcessed"] = True