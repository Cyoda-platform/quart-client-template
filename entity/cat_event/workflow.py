from datetime import datetime, timezone

async def process_add_timestamp(entity: dict):
    entity["timestamp"] = datetime.now(timezone.utc).isoformat()
    entity["workflowProcessed"] = True

async def process_send_notification(entity: dict):
    if entity.get("eventType") == "food_request" and entity.get("intensity", "").lower() == "dramatic":
        message = "Emergency! A cat demands snacks"
        notification_sent = await send_notification(message)

        notification_record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "message": message,
        }
        try:
            await entity_service.add_item(
                token=cyoda_auth_service,
                entity_model="notification",
                entity_version=ENTITY_VERSION,
                entity=notification_record,
                workflow=None
            )
        except Exception:
            logger.exception("Failed to add notification entity")

        entity["notificationSent"] = notification_sent
        entity["notificationMessage"] = message
    else:
        entity["notificationSent"] = False
        entity["notificationMessage"] = ""
    entity["workflowProcessed"] = True

async def condition_always_true(entity: dict) -> bool:
    return True