import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta

from quart import Blueprint, jsonify
from quart_schema import validate_request
from app_init.app_init import BeanFactory

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

routes_bp = Blueprint('routes', __name__)

factory = BeanFactory(config={'CHAT_REPOSITORY': 'cyoda'})
services = factory.get_services()
entity_service = services['entity_service']
cyoda_auth_service = services['cyoda_auth_service']

# Constants for egg cooking durations in seconds
EGG_COOK_TIMES = {
    "soft": 240,    # 4 minutes
    "medium": 420,  # 7 minutes
    "hard": 600,    # 10 minutes
}

entity_name = "alarm"  # entity name in underscore lowercase

# Utility to calculate time left
def time_left(end_time: datetime) -> int:
    now = datetime.utcnow()
    delta = end_time - now
    return max(int(delta.total_seconds()), 0)

# Background task to wait for alarm and notify user (mock notification)
async def alarm_timer(alarm_id: str):
    try:
        item = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model=entity_name,
            entity_version=None,
            technical_id=alarm_id
        )
        if not item:
            logger.info(f"Alarm {alarm_id} not found at timer start.")
            return
        end_time_str = item.get("end_time")
        if not end_time_str:
            logger.info(f"Alarm {alarm_id} missing end_time.")
            return
        end_time = datetime.fromisoformat(end_time_str)
        seconds_to_wait = time_left(end_time)
        if seconds_to_wait > 0:
            await asyncio.sleep(seconds_to_wait)
        # Update status to finished
        item["status"] = "finished"
        await entity_service.update_item(
            token=cyoda_auth_service,
            entity_model=entity_name,
            entity_version=None,
            entity=item,
            technical_id=alarm_id,
            meta={}
        )
        logger.info(f"Alarm {alarm_id} for {item.get('egg_type')} egg finished at {datetime.utcnow().isoformat()}")
        # TODO: Implement real notification logic here (push notification, email, etc.)
    except Exception as e:
        logger.exception(e)

# Workflow function applied asynchronously before persistence.
# This function takes the entity data as the only argument.
# You can change entity state inside this function.
# You can get and add entities of a different entity_model.
# You cannot add/update/delete current entity_model entities here.
async def process_alarm(entity):
    # Normalize status and timestamps
    if "status" not in entity or not entity["status"]:
        entity["status"] = "active"

    if "created_at" not in entity:
        entity["created_at"] = datetime.utcnow().isoformat()

    # Set end_time if missing, based on egg_type
    if "end_time" not in entity or not entity["end_time"]:
        egg_type = entity.get("egg_type")
        if egg_type not in EGG_COOK_TIMES:
            # If invalid egg_type, default to soft
            egg_type = "soft"
            entity["egg_type"] = egg_type
        duration = EGG_COOK_TIMES[egg_type]
        end_time = datetime.utcnow() + timedelta(seconds=duration)
        entity["end_time"] = end_time.isoformat()

    # Launch the async timer task to update status when alarm ends
    # We do this here because workflow supports async code and fire & forget
    # Use entity 'id' to identify the alarm; if missing, log and skip timer
    alarm_id = entity.get("id")
    if alarm_id:
        asyncio.create_task(alarm_timer(alarm_id))
    else:
        logger.warning("Alarm entity has no 'id' during workflow; timer not started.")

    return entity

@dataclass
class AlarmRequest:
    egg_type: str

@dataclass
class CancelRequest:
    alarm_id: str

@routes_bp.route("/api/alarm/set", methods=["POST"])
@validate_request(AlarmRequest)
async def set_alarm(data: AlarmRequest):
    egg_type = data.egg_type.lower()
    if egg_type not in EGG_COOK_TIMES:
        return jsonify({"status": "error", "message": "Invalid egg_type"}), 400

    # Clear all existing alarms (simulate single active alarm)
    existing_alarms = await entity_service.get_items(
        token=cyoda_auth_service,
        entity_model=entity_name,
        entity_version=None,
    )
    for alarm in existing_alarms:
        alarm_id = alarm.get("id")
        if alarm_id:
            await entity_service.delete_item(
                token=cyoda_auth_service,
                entity_model=entity_name,
                entity_version=None,
                technical_id=alarm_id,
                meta={}
            )

    # Create minimal alarm entity, full data and async timer handled by workflow
    alarm_data = {
        "egg_type": egg_type,
        # no end_time or status here, workflow sets them
    }

    alarm_id = await entity_service.add_item(
        token=cyoda_auth_service,
        entity_model=entity_name,
        entity_version=None,
        entity=alarm_data
    )

    return jsonify({
        "status": "success",
        "message": f"Alarm set for {egg_type}-boiled egg",
        "alarm_id": alarm_id,
        "duration_seconds": EGG_COOK_TIMES[egg_type],
    })

@routes_bp.route("/api/alarm/status", methods=["GET"])
async def get_alarm_status():
    # Get all alarms, expect only one active
    alarms = await entity_service.get_items(
        token=cyoda_auth_service,
        entity_model=entity_name,
        entity_version=None,
    )
    if not alarms:
        return jsonify({
            "alarm_id": None,
            "egg_type": None,
            "time_left_seconds": 0,
            "status": "none",
        })

    alarm = alarms[0]
    status = alarm.get("status")
    left = 0
    if status == "active":
        end_time_str = alarm.get("end_time")
        if end_time_str:
            try:
                end_time = datetime.fromisoformat(end_time_str)
                left = time_left(end_time)
            except Exception as e:
                logger.warning(f"Invalid end_time format in alarm status: {e}")
                left = 0

    return jsonify({
        "alarm_id": alarm.get("id"),
        "egg_type": alarm.get("egg_type"),
        "time_left_seconds": left,
        "status": status,
    })

@routes_bp.route("/api/alarm/cancel", methods=["POST"])
@validate_request(CancelRequest)
async def cancel_alarm(data: CancelRequest):
    alarm_id = data.alarm_id
    if not alarm_id:
        return jsonify({
            "status": "error",
            "message": "Invalid or unknown alarm_id"
        }), 400
    item = await entity_service.get_item(
        token=cyoda_auth_service,
        entity_model=entity_name,
        entity_version=None,
        technical_id=alarm_id
    )
    if not item:
        return jsonify({
            "status": "error",
            "message": "Invalid or unknown alarm_id"
        }), 400

    await entity_service.delete_item(
        token=cyoda_auth_service,
        entity_model=entity_name,
        entity_version=None,
        technical_id=alarm_id,
        meta={}
    )
    # TODO: If integrated with a real scheduler/task manager, cancel the task here

    return jsonify({
        "status": "success",
        "message": "Alarm cancelled"
    })