from typing import Dict
import asyncio
import logging

_logger = logging.getLogger(__name__)
_notification_sent_for_date = set()
_notification_lock = asyncio.Lock()

async def process_game(entity: Dict) -> None:
    """
    Workflow orchestration for game entity.
    """
    await process_normalize_status(entity)
    await process_send_notifications(entity)

async def process_normalize_status(entity: Dict) -> None:
    status = entity.get("Status")
    if status:
        entity["Status"] = status.upper()

async def process_send_notifications(entity: Dict) -> None:
    date_str = entity.get("Day")
    if not date_str:
        return

    async with _notification_lock:
        if date_str in _notification_sent_for_date:
            return
        _notification_sent_for_date.add(date_str)

    asyncio.create_task(_send_notifications_for_date(date_str))

async def _send_notifications_for_date(date_str: str) -> None:
    # TODO: Implement notification sending logic here
    _logger.info(f"Sending notifications for date {date_str}")
    await asyncio.sleep(0.1)  # simulate async work