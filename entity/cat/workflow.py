async def process_start_check_mood(entity: dict):
    entity["workflowProcessed"] = True

async def process_handle_calm_mood(entity: dict):
    entity["mood"] = "calm"
    entity["workflowProcessed"] = True

async def process_handle_playful_mood(entity: dict):
    entity["mood"] = "playful"
    entity["workflowProcessed"] = True

async def process_handle_agitated_mood(entity: dict):
    entity["mood"] = "agitated"
    entity["workflowProcessed"] = True

async def process_wait_until_calm(entity: dict):
    entity["waiting"] = True
    entity["workflowProcessed"] = True

async def process_cat_calms_down(entity: dict):
    entity["mood"] = "calm"
    entity["waiting"] = False
    entity["playing_with_cat"] = False
    entity["workflowProcessed"] = True

async def process_start_brushing(entity: dict):
    entity["brushing_started"] = True
    entity["workflowProcessed"] = True

async def process_continue_brushing(entity: dict):
    entity["brushing_continued"] = True
    entity["workflowProcessed"] = True

async def process_finish_brushing(entity: dict):
    entity["brushing_finished"] = True
    entity["workflowProcessed"] = True

async def process_stop_brushing(entity: dict):
    entity["brushing_stopped"] = True
    entity["workflowProcessed"] = True

async def process_engage_play(entity: dict):
    entity["playing_with_cat"] = True
    entity["workflowProcessed"] = True

async def process_is_cat_calm(entity: dict) -> bool:
    return entity.get("mood", "calm") == "calm"

async def process_is_cat_playful(entity: dict) -> bool:
    return entity.get("mood") == "playful"

async def process_is_cat_agitated(entity: dict) -> bool:
    return entity.get("mood") == "agitated"

async def process_is_cat_still_calm(entity: dict) -> bool:
    return entity.get("mood") == "calm" and entity.get("brushing_started", False) is True

async def process_is_brushing_complete(entity: dict) -> bool:
    return entity.get("brushing_continued", False) is True and entity.get("brushing_finished", False) is False