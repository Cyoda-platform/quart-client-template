from dataclasses import dataclass
import asyncio
import logging
from datetime import datetime
from typing import Optional

from quart import Blueprint, jsonify
from quart_schema import validate_request

from app_init.app_init import BeanFactory
from common.config.config import ENTITY_VERSION

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

routes_bp = Blueprint('routes', __name__)

factory = BeanFactory(config={'CHAT_REPOSITORY': 'cyoda'})
entity_service = factory.get_services()['entity_service']
cyoda_auth_service = factory.get_services()["cyoda_auth_service"]

EGG_COOK_TIMES = {"soft": 4, "medium": 7, "hard": 12}
ENTITY_NAME = "alarm"  # entity name underscore lowercase


@dataclass
class AlarmRequest:
    egg_type: str
    custom_time: Optional[str]


@dataclass
class DeleteRequest:
    alarm_id: str


async def fetch_external_time_api():
    try:
        import httpx
        async with httpx.AsyncClient() as client:
            r = await client.get("http://worldtimeapi.org/api/timezone/Etc/UTC")
            r.raise_for_status()
            data = r.json()
            current_time_iso = data.get("utc_datetime")
            return datetime.fromisoformat(current_time_iso.replace("Z", "+00:00"))
    except Exception:
        logger.exception("Failed to fetch current time from external API")
        return datetime.utcnow()


async def alarm_trigger(alarm_id: str):
    try:
        alarm = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model=ENTITY_NAME,
            entity_version=ENTITY_VERSION,
            technical_id=alarm_id
        )
        if not alarm:
            logger.warning(f"Alarm {alarm_id} not found for triggering")
            return
        set_time_str = alarm.get("set_time")
        if not set_time_str:
            logger.warning(f"Alarm {alarm_id} missing set_time")
            return
        set_time = datetime.fromisoformat(set_time_str)
        now = datetime.utcnow()
        wait_seconds = (set_time - now).total_seconds()
        if wait_seconds > 0:
            await asyncio.sleep(wait_seconds)
        # update status to triggered
        alarm["status"] = "triggered"
        await entity_service.update_item(
            token=cyoda_auth_service,
            entity_model=ENTITY_NAME,
            entity_version=ENTITY_VERSION,
            entity=alarm,
            technical_id=alarm_id,
            meta={}
        )
        logger.info(f"Alarm triggered: {alarm_id} for {alarm['egg_type']} egg at {set_time.isoformat()}")
        # TODO: Extend to send real notification
    except Exception:
        logger.exception(f"Exception during alarm trigger for {alarm_id}")


@routes_bp.route("/alarm", methods=["POST"])
@validate_request(AlarmRequest)
async def set_alarm(data: AlarmRequest):
    try:
        entity_dict = data.__dict__
        alarm_id = await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model=ENTITY_NAME,
            entity_version=ENTITY_VERSION,
            entity=entity_dict
        )
        asyncio.create_task(alarm_trigger(alarm_id))

        alarm = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model=ENTITY_NAME,
            entity_version=ENTITY_VERSION,
            technical_id=alarm_id
        )

        return jsonify({
            "alarm_id": alarm_id,
            "set_time": alarm.get("set_time"),
            "egg_type": alarm.get("egg_type"),
            "status": alarm.get("status")
        }), 201
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": str(e)}), 400


@routes_bp.route("/alarms", methods=["GET"])
async def get_alarms():
    try:
        all_alarms = await entity_service.get_items(
            token=cyoda_auth_service,
            entity_model=ENTITY_NAME,
            entity_version=ENTITY_VERSION,
        )
        active_alarms = []
        now = datetime.utcnow()
        for alarm in all_alarms:
            status = alarm.get("status")
            if status not in ("triggered", "deleted"):
                set_time_str = alarm.get("set_time")
                if not set_time_str:
                    continue
                set_time = datetime.fromisoformat(set_time_str)
                if set_time > now:
                    active_alarms.append({
                        "alarm_id": alarm.get("alarm_id") or alarm.get("technical_id") or "",
                        "set_time": set_time.isoformat(),
                        "egg_type": alarm.get("egg_type"),
                        "status": "active"
                    })
        return jsonify(active_alarms), 200
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": str(e)}), 500


@routes_bp.route("/alarm/delete", methods=["POST"])
@validate_request(DeleteRequest)
async def delete_alarm(data: DeleteRequest):
    try:
        alarm_id = str(data.alarm_id)
        alarm = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model=ENTITY_NAME,
            entity_version=ENTITY_VERSION,
            technical_id=alarm_id
        )
        if not alarm:
            return jsonify({"error": "Alarm not found"}), 404
        alarm["status"] = "deleted"
        await entity_service.update_item(
            token=cyoda_auth_service,
            entity_model=ENTITY_NAME,
            entity_version=ENTITY_VERSION,
            entity=alarm,
            technical_id=alarm_id,
            meta={}
        )
        # TODO: Optionally cancel pending alarm trigger task if implemented
        return jsonify({"alarm_id": alarm_id, "status": "deleted"}), 200
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": str(e)}), 400