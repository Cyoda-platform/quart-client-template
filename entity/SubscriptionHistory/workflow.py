import logging
from datetime import datetime

logger = logging.getLogger(__name__)

async def record_subscribe_action(entity: dict):
    entity["action"] = "subscribe"
    entity["timestamp"] = datetime.utcnow().isoformat()
    entity["details"] = {
        "previous_status": entity.get("previous_status", "none"),
        "new_status": "active",
        "cat_fact_sent": None
    }
    entity["workflowProcessed"] = True

async def record_unsubscribe_action(entity: dict):
    entity["action"] = "unsubscribe"
    entity["timestamp"] = datetime.utcnow().isoformat()
    entity["details"] = {
        "previous_status": entity.get("previous_status", "active"),
        "new_status": "none",
        "cat_fact_sent": None
    }
    entity["workflowProcessed"] = True

async def record_email_sent_action(entity: dict):
    entity["action"] = "send_email"
    entity["timestamp"] = datetime.utcnow().isoformat()
    entity["details"] = {
        "cat_fact_sent": entity.get("cat_fact_sent", ""),
        "status": entity.get("email_status", "success")
    }
    entity["workflowProcessed"] = True

async def record_interaction_action(entity: dict):
    entity["action"] = "user_interaction"
    entity["timestamp"] = datetime.utcnow().isoformat()
    entity["details"] = entity.get("interaction_details", {})
    entity["workflowProcessed"] = True