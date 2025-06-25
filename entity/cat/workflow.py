async def start_check_mood(entity: dict):
    entity["workflowProcessed"] = True

async def handle_calm_mood(entity: dict):
    entity["mood"] = "calm"
    entity["workflowProcessed"] = True

async def handle_playful_mood(entity: dict):
    entity["mood"] = "playful"
    entity["workflowProcessed"] = True

async def handle_agitated_mood(entity: dict):
    entity["mood"] = "agitated"
    entity["workflowProcessed"] = True

async def start_brushing(entity: dict):
    entity["brushing_started"] = True
    entity["workflowProcessed"] = True

async def engage_play(entity: dict):
    entity["playing_with_cat"] = True
    entity["workflowProcessed"] = True

async def wait_until_calm(entity: dict):
    entity["waiting"] = True
    entity["workflowProcessed"] = True

async def cat_calms_down(entity: dict):
    entity["mood"] = "calm"
    entity["waiting"] = False
    entity["playing_with_cat"] = False
    entity["workflowProcessed"] = True

async def continue_brushing(entity: dict):
    entity["brushing_continued"] = True
    entity["workflowProcessed"] = True

async def finish_brushing(entity: dict):
    entity["brushing_finished"] = True
    entity["workflowProcessed"] = True

async def stop_brushing(entity: dict):
    entity["brushing_stopped"] = True
    entity["workflowProcessed"] = True