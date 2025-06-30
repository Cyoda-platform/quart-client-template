async def start_preparation(entity: dict):
    entity["status"] = "preparation_started"
    entity["workflowProcessed"] = True

async def finish_grooming(entity: dict):
    entity["grooming_done"] = True
    entity["grooming_complete"] = True
    entity["workflowProcessed"] = True

async def is_health_ok(entity: dict) -> bool:
    return entity.get("health_status", "") == "ok"

async def is_health_not_ok(entity: dict) -> bool:
    return entity.get("health_status", "") != "ok"

async def approve_health_check(entity: dict):
    entity["health_check_approved"] = True
    entity["workflowProcessed"] = True

async def schedule_veterinary_care(entity: dict):
    entity["veterinary_care_scheduled"] = True
    entity["workflowProcessed"] = True

async def finish_veterinary_care(entity: dict):
    entity["veterinary_care_done"] = True
    entity["workflowProcessed"] = True

async def complete_training(entity: dict):
    entity["training_completed"] = True
    entity["workflowProcessed"] = True

async def start_exhibition(entity: dict):
    entity["exhibition_started"] = True
    entity["workflowProcessed"] = True

async def finish_exhibition(entity: dict):
    entity["exhibition_done"] = True
    entity["workflowProcessed"] = True