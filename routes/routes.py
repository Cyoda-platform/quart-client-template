from datetime import timezone, datetime
import logging
from quart import Blueprint, request, abort, jsonify
from quart_schema import validate, validate_querystring, tag, operation_id
from app_init.app_init import BeanFactory
import asyncio
import uuid
import httpx

logger = logging.getLogger(__name__)

FINAL_STATES = {'FAILURE', 'SUCCESS', 'CANCELLED', 'CANCELLED_BY_USER', 'UNKNOWN', 'FINISHED'}
PROCESSING_STATE = 'PROCESSING'

routes_bp = Blueprint('routes', __name__)

factory = BeanFactory(config={'CHAT_REPOSITORY': 'cyoda'})
entity_service = factory.get_services()['entity_service']
cyoda_auth_service = factory.get_services()["cyoda_auth_service"]

ENTITY_SUBSCRIBER = "subscriber"
ENTITY_CATFACT_REQUEST = "catfact_request"
ENTITY_LAST_CAT_FACT = "last_cat_fact"

_stats_lock = asyncio.Lock()
_email_stats = {
    "emailsSent": 0,
    "emailsOpened": 0,
    "clicks": 0,
}

@routes_bp.route("/api/subscribe", methods=["POST"])
@validate
async def subscribe():
    data = await request.get_json()
    email = data.get("email")
    if not email:
        abort(400, "Missing email field")
    entity_data = {"email": email}
    try:
        id = await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model=ENTITY_SUBSCRIBER,
            entity_version=None,
            entity=entity_data
        )
    except Exception as e:
        logger.exception(e)
        abort(500, "Failed to add subscriber")
    subscriber_id = str(uuid.uuid4())
    return jsonify({"message": "Subscription successful", "subscriberId": subscriber_id, "entityId": id})

@routes_bp.route("/api/fetch-and-send", methods=["POST"])
@validate
async def fetch_and_send():
    try:
        id = await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model=ENTITY_CATFACT_REQUEST,
            entity_version=None,
            entity={}
        )
    except Exception as e:
        logger.exception(e)
        abort(500, "Failed to initiate cat fact sending")
    return jsonify({"message": "Cat fact request submitted", "entityId": id})

@routes_bp.route("/api/reporting/summary", methods=["GET"])
async def reporting_summary():
    try:
        subscribers = await entity_service.get_items(
            token=cyoda_auth_service,
            entity_model=ENTITY_SUBSCRIBER,
            entity_version=None,
        )
        total_subscribers = len(subscribers)
    except Exception as e:
        logger.exception(e)
        total_subscribers = 0

    async with _stats_lock:
        emails_sent = _email_stats["emailsSent"]
        emails_opened = _email_stats["emailsOpened"]
        clicks = _email_stats["clicks"]

    return jsonify({
        "totalSubscribers": total_subscribers,
        "emailsSent": emails_sent,
        "emailsOpened": emails_opened,
        "clicks": clicks,
    })

# Additional internal helper functions can be added below if needed, but no startup/shutdown logic here.