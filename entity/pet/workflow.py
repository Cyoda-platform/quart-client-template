async def process_register_pet(entity: dict):
    entity["status"] = "registered"
    entity["workflowProcessed"] = True

async def process_vet_checkup(entity: dict):
    entity["vet_checkup"] = "completed"
    entity["workflowProcessed"] = True

async def process_update_health_status(entity: dict):
    entity["health_status"] = "updated"
    entity["workflowProcessed"] = True

async def process_deactivate_pet(entity: dict):
    entity["status"] = "deactivated"
    entity["workflowProcessed"] = True