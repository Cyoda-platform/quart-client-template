import logging
from datetime import datetime

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

async def process_validate_email_details(entity: dict):
    email = entity.get("recipientEmail")
    subject = entity.get("subject")
    if not email or "@" not in email:
        entity["processingStatus"] = "failed"
        entity["processingError"] = "Invalid or missing recipient email"
        entity["processedAt"] = datetime.utcnow().isoformat()
        entity["deliveryStatus"] = "failed"
    else:
        entity["processingStatus"] = "validated"
        entity["validatedAt"] = datetime.utcnow().isoformat()

async def process_set_delivery_pending(entity: dict):
    entity["deliveryStatus"] = "pending"
    entity["deliveryPendingAt"] = datetime.utcnow().isoformat()

async def process_prepare_email_content(entity: dict):
    pet_details = entity.get("petDetails", {})
    name = pet_details.get("name", "Unknown")
    category = pet_details.get("category", "Unknown")
    status = pet_details.get("status", "Unknown")
    body = f"""Dear User,

Here are the details of your pet:
- Name: {name}
- Category: {category}
- Status: {status}

Thank you for using our service!

Best Regards,
Pet Service Team"""
    entity["body"] = body
    entity["contentPreparedAt"] = datetime.utcnow().isoformat()
    entity["processingStatus"] = "content_prepared"

async def process_send_email(entity: dict):
    try:
        # TODO: Implement actual email sending logic here
        # For prototype, simulate sending by setting sentAt
        entity["sentAt"] = datetime.utcnow().isoformat()
        entity["deliveryStatus"] = "sent"
        entity["processingStatus"] = "completed"
    except Exception as e:
        logger.exception(f"Failed to send email: {e}")
        entity["deliveryStatus"] = "failed"
        entity["processingStatus"] = "failed"
        entity["processingError"] = str(e)
        entity["processedAt"] = datetime.utcnow().isoformat()

async def process_set_delivery_sent(entity: dict):
    entity["deliveryStatus"] = "sent"
    entity["deliverySentAt"] = datetime.utcnow().isoformat()

async def process_handle_failure(entity: dict):
    entity["deliveryStatus"] = "failed"
    entity["processingStatus"] = "failed"
    entity["processedAt"] = datetime.utcnow().isoformat()

async def process_set_delivery_failed(entity: dict):
    entity["deliveryStatus"] = "failed"
    entity["deliveryFailedAt"] = datetime.utcnow().isoformat()