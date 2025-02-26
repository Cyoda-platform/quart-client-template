import asyncio
import datetime

# Business logic: mark the entity as processed
def process_mark_as_processed(entity):
    entity["workflowProcessed"] = True
    entity["processedAt"] = datetime.datetime.utcnow().isoformat()

# Business logic: log email stats
async def process_log_email_stats(entity):
    try:
        await asyncio.sleep(0.1)
        print(f"Email stats processed for record {entity.get('id', 'unknown')} with totalEmailsSent: {entity.get('totalEmailsSent', 0)}")
    except Exception as e:
        print(f"Error in log_email_stats: {e}")