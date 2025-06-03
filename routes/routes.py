import asyncio
import logging
from datetime import datetime, timedelta
from dataclasses import dataclass

from quart import Quart, jsonify
from quart_schema import QuartSchema, validate_request

from app_init.app_init import BeanFactory
from common.config.config import ENTITY_VERSION

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

factory = BeanFactory(config={'CHAT_REPOSITORY': 'cyoda'})
entity_service = factory.get_services()['entity_service']
cyoda_auth_service = factory.get_services()["cyoda_auth_service"]

app = Quart(__name__)
QuartSchema(app)

@dataclass
class AlarmRequest:
    egg_type: str

EGG_TIMES = {"soft": 240, "medium": 420, "hard": 600}

# Local storage for alarm countdown tasks
_local_alarm_tasks = {}

def set_local_alarm_task(alarm_id: str, task: asyncio.Task):
    _local_alarm_tasks[alarm_id] = task

def get_local_alarm_task(alarm_id: str):
    return _local_alarm_tasks.get(alarm_id)

def clear_local_alarm_task(alarm_id: str):
    _local_alarm_tasks.pop(alarm_id, None)

async def get_active_alarm():
    try:
        condition = {
            "cyoda": {
                "type": "group",
                "operator": "AND",
                "conditions": [
                    {
                        "jsonPath": "$.status",
                        "operatorType": "EQUALS",
                        "value": "active",
                        "type": "simple"
                    }
                ]
            }
        }
        alarms_list = await entity_service.get_items_by_condition(
            token=cyoda_auth_service,
            entity_model="alarm",
            entity_version=ENTITY_VERSION,
            condition=condition
        )
    except Exception as e:
        logger.exception(e)
        return None, None

    now = datetime.utcnow()
    for alarm in alarms_list:
        alarm_id = alarm.get("technical_id") or alarm.get("id")
        if not alarm_id:
            continue
        try:
            end_time = datetime.fromisoformat(alarm["end_time"])
        except Exception:
            continue

        if end_time > now:
            return str(alarm_id), alarm
        else:
            # Mark expired alarms as finished
            if alarm.get("status") == "active":
                alarm["status"] = "finished"
                try:
                    await entity_service.update_item(
                        token=cyoda_auth_service,
                        entity_model="alarm",
                        entity_version=ENTITY_VERSION,
                        entity=alarm,
                        technical_id=str(alarm_id),
                        meta={}
                    )
                except Exception as e:
                    logger.exception(e)

    return None, None

async def alarm_countdown_task(alarm_id: str, end_time_iso: str):
    try:
        end_time = datetime.fromisoformat(end_time_iso)
    except Exception:
        logger.warning(f"Invalid end_time format for alarm {alarm_id}")
        return

    now = datetime.utcnow()
    delay = (end_time - now).total_seconds()
    if delay > 0:
        logger.info(f"Alarm {alarm_id} countdown started for {delay:.1f} seconds.")
        try:
            await asyncio.sleep(delay)
        except asyncio.CancelledError:
            logger.info(f"Alarm {alarm_id} countdown cancelled.")
            return

    # Countdown finished - update status to finished and notify user
    logger.info(f"Alarm {alarm_id} finished! Notify user: sound + message.")
    try:
        alarm = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model="alarm",
            entity_version=ENTITY_VERSION,
            technical_id=alarm_id
        )
        if not alarm:
            logger.warning(f"Alarm {alarm_id} not found at countdown end.")
            return

        alarm["status"] = "finished"
        await entity_service.update_item(
            token=cyoda_auth_service,
            entity_model="alarm",
            entity_version=ENTITY_VERSION,
            entity=alarm,
            technical_id=alarm_id,
            meta={}
        )
    except Exception as e:
        logger.exception(e)
    finally:
        clear_local_alarm_task(alarm_id)

# Workflow function for 'alarm' entity

# POST endpoint
@app.route("/api/alarm/set", methods=["POST"])
@validate_request(AlarmRequest)
async def set_alarm(data: AlarmRequest):
    egg_type = data.egg_type
    if egg_type not in EGG_TIMES:
        return jsonify({"error": "Invalid egg_type, allowed: soft, medium, hard"}), 400

    # Cancel existing active alarm - must stay here due to recursion restriction
    active_alarm_id, active_alarm = await get_active_alarm()
    if active_alarm_id:
        active_alarm["status"] = "cancelled"
        try:
            await entity_service.update_item(
                token=cyoda_auth_service,
                entity_model="alarm",
                entity_version=ENTITY_VERSION,
                entity=active_alarm,
                technical_id=active_alarm_id,
                meta={}
            )
            logger.info(f"Cancelled existing alarm {active_alarm_id} to set a new one.")
            # Cancel local task if running
            task = get_local_alarm_task(active_alarm_id)
            if task and not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    logger.info(f"Cancelled countdown task for alarm {active_alarm_id}.")
            clear_local_alarm_task(active_alarm_id)
        except Exception as e:
            logger.exception(e)

    now = datetime.utcnow()
    duration_seconds = EGG_TIMES[egg_type]
    end_time = now + timedelta(seconds=duration_seconds)

    alarm_data = {
        "egg_type": egg_type,
        "duration_seconds": duration_seconds,
        "start_time": now.isoformat(),
        "end_time": end_time.isoformat(),
        "status": "active"
    }

    try:
        alarm_id = await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model="alarm",
            entity_version=ENTITY_VERSION,
            entity=alarm_data
        )
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to create alarm"}), 500

    # Start countdown task after persistence, as we now have alarm_id
    task = asyncio.create_task(alarm_countdown_task(alarm_id, alarm_data["end_time"]))
    set_local_alarm_task(alarm_id, task)

    logger.info(f"Set alarm {alarm_id} for {egg_type} egg for {duration_seconds} seconds.")

    return jsonify({
        "alarm_id": alarm_id,
        "egg_type": egg_type,
        "duration_seconds": duration_seconds,
        "status": "active"
    })

@app.route("/api/alarm/status", methods=["GET"])
async def get_alarm_status():
    active_alarm_id, alarm = await get_active_alarm()
    if not alarm:
        return jsonify({
            "alarm_id": None,
            "egg_type": None,
            "time_remaining_seconds": None,
            "status": "inactive"
        })

    now = datetime.utcnow()
    try:
        end_time = datetime.fromisoformat(alarm["end_time"])
    except Exception:
        logger.warning(f"Invalid end_time format for alarm {active_alarm_id}")
        end_time = now

    time_remaining = max(0, int((end_time - now).total_seconds()))
    return jsonify({
        "alarm_id": active_alarm_id,
        "egg_type": alarm.get("egg_type"),
        "time_remaining_seconds": time_remaining,
        "status": alarm.get("status")
    })

@app.route("/api/alarm/cancel", methods=["POST"])
async def cancel_alarm():
    active_alarm_id, alarm = await get_active_alarm()
    if not alarm:
        return jsonify({
            "alarm_id": None,
            "status": "no_active_alarm"
        })

    task = get_local_alarm_task(active_alarm_id)
    if task and not task.done():
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            logger.info(f"Alarm countdown task for {active_alarm_id} cancelled.")

    alarm["status"] = "cancelled"
    try:
        await entity_service.update_item(
            token=cyoda_auth_service,
            entity_model="alarm",
            entity_version=ENTITY_VERSION,
            entity=alarm,
            technical_id=active_alarm_id,
            meta={}
        )
        logger.info(f"Alarm {active_alarm_id} cancelled by user.")
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to cancel alarm"}), 500

    clear_local_alarm_task(active_alarm_id)

    return jsonify({
        "alarm_id": active_alarm_id,
        "status": "cancelled"
    })

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)