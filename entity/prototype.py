import asyncio
import logging
import uuid
from datetime import datetime, timedelta
from dataclasses import dataclass

from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

@dataclass
class AlarmRequest:
    egg_type: str

# POST - route first, validation last due to validate_request defect workaround
@app.route("/api/alarm/set", methods=["POST"])
@validate_request(AlarmRequest)
async def set_alarm(data: AlarmRequest):
    egg_type = data.egg_type
    if egg_type not in ("soft", "medium", "hard"):
        return jsonify({"error": "Invalid egg_type, allowed: soft, medium, hard"}), 400

    # Cancel any existing active alarm
    active_alarm_id, active_alarm = await get_active_alarm()
    if active_alarm_id:
        active_alarm["status"] = "cancelled"
        logger.info(f"Cancelled existing alarm {active_alarm_id} to set a new one.")

    duration_seconds = EGG_TIMES[egg_type]
    alarm_id = str(uuid.uuid4())
    now = datetime.utcnow()
    end_time = now + timedelta(seconds=duration_seconds)

    alarms[alarm_id] = {
        "egg_type": egg_type,
        "duration_seconds": duration_seconds,
        "start_time": now,
        "end_time": end_time,
        "status": "active",
        "task": None
    }

    alarms[alarm_id]["task"] = asyncio.create_task(alarm_countdown(alarm_id))
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
    time_remaining = max(0, int((alarm["end_time"] - now).total_seconds()))
    return jsonify({
        "alarm_id": active_alarm_id,
        "egg_type": alarm["egg_type"],
        "time_remaining_seconds": time_remaining,
        "status": alarm["status"]
    })

@app.route("/api/alarm/cancel", methods=["POST"])
async def cancel_alarm():
    active_alarm_id, alarm = await get_active_alarm()
    if not alarm:
        return jsonify({
            "alarm_id": None,
            "status": "no_active_alarm"
        })

    task = alarm.get("task")
    if task and not task.done():
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            logger.info(f"Alarm countdown task for {active_alarm_id} cancelled.")

    alarm["status"] = "cancelled"
    logger.info(f"Alarm {active_alarm_id} cancelled by user.")

    return jsonify({
        "alarm_id": active_alarm_id,
        "status": "cancelled"
    })

# Mock in-memory storage and helpers

alarms = {}
EGG_TIMES = {"soft": 240, "medium": 420, "hard": 600}

async def get_active_alarm():
    now = datetime.utcnow()
    for aid, alarm in alarms.items():
        if alarm["status"] == "active" and alarm["end_time"] > now:
            return aid, alarm
        if alarm["status"] == "active" and alarm["end_time"] <= now:
            alarm["status"] = "finished"
    return None, None

async def alarm_countdown(alarm_id: str):
    alarm = alarms.get(alarm_id)
    if not alarm:
        return
    now = datetime.utcnow()
    delay = (alarm["end_time"] - now).total_seconds()
    if delay > 0:
        logger.info(f"Alarm {alarm_id} countdown started for {delay:.1f} seconds.")
        try:
            await asyncio.sleep(delay)
        except asyncio.CancelledError:
            logger.info(f"Alarm {alarm_id} countdown cancelled.")
            return
    # TODO: real notification (sound/message)
    logger.info(f"Alarm {alarm_id} finished! Notify user: sound + message.")
    alarm["status"] = "finished"

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)