async def process_feed_cat(entity: dict):
    # Implement logic to feed the cat entity
    final_result = f"{entity['name']} has been fed."
    entity["final_result"] = final_result
    entity["workflowProcessed"] = True

async def process_play_with_cat(entity: dict):
    # Implement logic to play with the cat entity
    final_result = f"{entity['name']} has played with you."
    entity["final_result"] = final_result
    entity["workflowProcessed"] = True