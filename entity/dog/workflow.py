async def start_brushing(entity: dict):
    entity["status"] = "Brushing started"
    entity["workflowProcessed"] = True

async def pick_brush(entity: dict):
    entity["brush"] = "picked"
    entity["workflowProcessed"] = True

async def move_to_rabbit(entity: dict):
    entity["position"] = "near_rabbit"
    entity["workflowProcessed"] = True

async def calm_down_rabbit(entity: dict):
    entity["rabbit_state"] = "calmed"
    entity["workflowProcessed"] = True

async def brush_stroke(entity: dict):
    if "brush_strokes" not in entity:
        entity["brush_strokes"] = 0
    entity["brush_strokes"] += 1
    entity["workflowProcessed"] = True

async def end_brushing(entity: dict):
    entity["status"] = "Brushing finished"
    entity["workflowProcessed"] = True