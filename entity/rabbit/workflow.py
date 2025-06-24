async def process_transition_to_state_01(entity: dict):
    # Example processing logic for transition_to_state_01
    entity["step"] = "started at state_01"
    entity["workflowProcessed"] = False

async def process_transition_to_state_02(entity: dict):
    # Example processing logic for transition_to_state_02
    entity["step"] = "moved to state_02"
    entity["workflowProcessed"] = False

async def process_transition_with_condition_simple(entity: dict):
    # Example condition check logic returning bool as part of condition
    # For example, check if entity has attribute 'cleaned' set to True
    entity["condition_met"] = entity.get("cleaned", False)
    entity["workflowProcessed"] = False

async def process_transition_with_condition_simple_returns_bool(entity: dict) -> bool:
    # Returns boolean for transition condition
    return entity.get("cleaned", False)

async def process_transition_with_condition_group(entity: dict):
    # Example group condition processing logic
    # For example, check if entity rabbit attribute matches template_value_01 ignoring case
    rabbit_name = entity.get("rabbit", "").lower()
    expected_name = "template_value_01".lower()
    entity["group_condition_met"] = (rabbit_name == expected_name)
    entity["workflowProcessed"] = True

async def process_brush_rabbit(entity: dict):
    # Template example for brushing rabbit entity
    if "rabbit" in entity:
        entity["rabbit_brushed"] = True
    entity["workflowProcessed"] = True