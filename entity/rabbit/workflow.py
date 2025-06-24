async def start_brush(entity: dict):
    entity["status"] = "starting brush process"
    entity["workflowProcessed"] = True

async def gather_brush_tools(entity: dict):
    entity["brush_tools_ready"] = True
    entity["workflowProcessed"] = True

async def move_towards_rabbit(entity: dict):
    entity["position"] = "near_rabbit"
    entity["workflowProcessed"] = True

async def is_rabbit_calm(entity: dict) -> bool:
    return entity.get("rabbit_mood", "") == "calm"

async def is_rabbit_not_calm(entity: dict) -> bool:
    return entity.get("rabbit_mood", "") != "calm"

async def calm_rabbit_down(entity: dict):
    entity["rabbit_mood"] = "calm"
    entity["workflowProcessed"] = True

async def brush_fur(entity: dict):
    brushed = entity.get("fur_brushed", 0)
    entity["fur_brushed"] = brushed + 1
    entity["workflowProcessed"] = True

async def is_brushing_complete(entity: dict) -> bool:
    return entity.get("fur_brushed", 0) >= entity.get("fur_brush_goal", 5)

async def is_brushing_not_complete(entity: dict) -> bool:
    return entity.get("fur_brushed", 0) < entity.get("fur_brush_goal", 5)

async def end_brush(entity: dict):
    entity["status"] = "brushing completed"
    entity["workflowProcessed"] = True