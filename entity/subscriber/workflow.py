import asyncio
import datetime

# Simulate email sending workflow
async def process_send_welcome_email(entity):
    try:
        # Simulate sending a welcome email (replace with real email integration)
        await asyncio.sleep(0.1)
        print(f"Welcome email sent to {entity['email']}")
    except Exception as e:
        # Log exception if needed
        print(f"Error sending welcome email to {entity['email']}: {e}")

# Process entity to mark it as processed
def process_mark_as_processed(entity):
    entity["workflowProcessed"] = True
    entity["processedAt"] = datetime.datetime.utcnow().isoformat()