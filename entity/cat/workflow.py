async def process_transition_to_process(entity: dict):
    entity["action"] = "start brushing cat"
    entity["workflowProcessed"] = True

async def process_transition_to_decision(entity: dict):
    # Template example: check if cat is cooperative
    entity["cat_is_cooperative"] = True  # Example placeholder
    entity["workflowProcessed"] = True

async def process_transition_to_end_returns_bool(entity: dict) -> bool:
    # Example condition: brushing done successfully
    return entity.get("cat_is_cooperative", False)