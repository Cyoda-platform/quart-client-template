async def process_add_timestamp(entity: dict):
    entity["timestamp"] = datetime.now(timezone.utc).isoformat()

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

async def process_cat_event(entity: dict):
    # Orchestration only
    await process_add_timestamp(entity)
    await process_send_notification(entity)