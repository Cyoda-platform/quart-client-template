from datetime import datetime
import asyncio
import uuid

EXTERNAL_API_URL = "https://test-api.k6.io/public/crocodiles/"

def process_add_timestamp(entity):
    # Add a processed timestamp to the entity.
    entity["processed_at"] = datetime.utcnow().isoformat() + "Z"

def process_assign_id(entity):
    # Ensure the entity has a unique id.
    if "id" not in entity:
        entity["id"] = str(uuid.uuid4())

async def process_send_notification(entity):
    try:
        # Simulate async work like sending a notification.
        await asyncio.sleep(0.1)
        print(f"Notification: Entity {entity.get('id', 'unknown')} processed.")
    except Exception as e:
        # Log error but do not interrupt the workflow.
        print(f"Error sending notification: {e}")