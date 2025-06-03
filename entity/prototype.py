```python
import asyncio
import logging
import uuid
from datetime import datetime, timedelta

from quart import Quart, jsonify, request
from quart_schema import QuartSchema

import httpx

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# Mock in-memory "persistence" for alarms keyed by alarm_id
# Structure: {alarm_id: {egg_type, duration_seconds, end_time, status}}
alarms = {}

# Egg type to duration mapping (seconds)
EGG_TIMES = {
    "soft": 240,    # 4 minutes
    "medium": 420,  # 7 minutes
    "hard": 600     # 10 minutes
}

# Helper to get current active alarm if any (only one active alarm at a time)
async def get_active_alarm():
    now = datetime.utcnow()
    for alarm_id, alarm in alarms.items():
        if alarm["status"] == "active" and alarm["end_time"] > now:
            return alarm_id, alarm
        elif alarm["status"] == "active" and alarm["end_time"] <= now:
            # Alarm expired but status still active, mark it as finished
            alarm["status"] = "finished"
    return None, None


# Background task to wait for alarm and notify (mock notification)
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

    # TODO: Real notification (sound/message) should be triggered here.
    logger.info(f"Alarm {alarm_id} finished! Notify user: sound + message.")
    alarm["status"] = "finished"


@app.route("/api/alarm/set", methods=["POST"])
async def set_alarm():
    data = await request.get_json()
    egg_type = data.get("egg_type")

    if egg_type not in EGG_TIMES:
        return jsonify({"error": "Invalid egg_type, allowed: soft, medium, hard"}), 400

    # Cancel existing active alarm if any
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
        "task": None  # Will hold asyncio.Task for countdown
    }

    # Fire and forget alarm countdown task
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

    # Cancel countdown task
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


if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
```
