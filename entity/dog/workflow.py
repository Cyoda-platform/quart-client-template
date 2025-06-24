async def start_brushing(entity: dict):  
    entity["status"] = "Brushing started"  
    entity["workflowProcessed"] = True  

async def pick_brush(entity: dict):  
    entity["brush"] = "selected"  
    entity["workflowProcessed"] = True  

async def move_to_rabbit(entity: dict):  
    entity["position"] = "next to rabbit"  
    entity["workflowProcessed"] = True  

async def perform_brushing(entity: dict):  
    if "brushed_times" not in entity:  
        entity["brushed_times"] = 0  
    entity["brushed_times"] += 1  
    entity["status"] = f"Brushed {entity['brushed_times']} times"  
    entity["workflowProcessed"] = True  

async def is_brushing_done(entity: dict) -> bool:  
    return entity.get("brushed_times", 0) >= 3  

async def is_brushing_not_done(entity: dict) -> bool:  
    return entity.get("brushed_times", 0) < 3  

async def end_brushing(entity: dict):  
    entity["status"] = "Brushing finished"  
    entity["workflowProcessed"] = True