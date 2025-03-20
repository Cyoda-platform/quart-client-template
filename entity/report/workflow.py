import asyncio
import logging
from datetime import datetime

# Business logic: mark the report entity as processed.
async def process_mark_as_processed(entity: dict):
    entity["workflow_processed"] = True
    return entity

# Business logic: simulate report creation by adding report details.
async def process_create_report(entity: dict):
    entity["report_created_at"] = datetime.utcnow().isoformat()
    entity["report_status"] = "generated"
    return entity