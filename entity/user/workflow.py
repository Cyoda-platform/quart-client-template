import asyncio

async def evaluate_event(entity: dict):
    # Placeholder for event evaluation logic
    entity["event_evaluated"] = True
    entity["workflowProcessed"] = True

async def send_notification(entity: dict):
    # Placeholder for sending notification logic
    entity["notification_sent"] = True
    entity["workflowProcessed"] = True

async def is_dramatic_food_request(entity: dict) -> bool:
    # Check if the entity represents a dramatic food request
    request = entity.get("request", "").lower()
    dramatic_keywords = ["urgent", "immediately", "now", "dramatic", "emergency"]
    return any(word in request for word in dramatic_keywords)

async def is_not_dramatic_food_request(entity: dict) -> bool:
    return not await is_dramatic_food_request(entity)