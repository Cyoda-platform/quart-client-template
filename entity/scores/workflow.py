import asyncio
from datetime import datetime

# Business logic: add processing timestamp to the entity.
def process_add_timestamp(entity):
    entity["workflowProcessedAt"] = datetime.utcnow().isoformat() + "Z"

# Business logic: check if a significant event was triggered.
def process_check_event_triggered(entity):
    return bool(entity.get("eventTriggered"))

# Business logic: send a score notification.
async def process_send_score_notification(entity):
    try:
        # Simulate sending notification with a small delay.
        await asyncio.sleep(0.1)
        print(f"Notifying subscribers about game {entity.get('gameId')} update.")
    except Exception as e:
        print(f"Notification error for game {entity.get('gameId')}: {e}")

# Workflow orchestration: orchestrates processing of scores.
async def process_scores(entity):
    # Apply business logic to add a processing timestamp.
    process_add_timestamp(entity)
    # Check if the eventTriggered flag is set.
    if process_check_event_triggered(entity):
        # Fire-and-forget async notification.
        asyncio.create_task(process_send_score_notification(entity))
    return entity