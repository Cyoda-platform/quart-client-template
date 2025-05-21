async def process_create_pet(entity: dict):
    entity["status"] = "created"
    entity["workflowProcessed"] = True

async def process_update_pet(entity: dict):
    entity["status"] = "updated"
    entity["workflowProcessed"] = True

async def process_delete_pet(entity: dict):
    entity["status"] = "deleted"
    entity["workflowProcessed"] = True