import asyncio
import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta

from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# Constants for egg cooking durations in seconds
EGG_COOK_TIMES = {
    "soft": 240,    # 4 minutes
    "medium": 420,  # 7 minutes
    "hard": 600,    # 10 minutes
}

# In-memory "cache" for one active alarm (simulate persistence)
# Structure: { alarm_id: { "egg_type": str, "end_time": datetime, "status": str } }
active_alarm = {}

# Utility to calculate time left
def time_left(end_time: datetime) -> int:
    now = datetime.utcnow()
    delta = end_time - now
    return max(int(delta.total_seconds()), 0)

# Background task to wait for alarm and notify user (mock notification)
async def alarm_timer(alarm_id: str):
    try:
        alarm = active_alarm.get(alarm_id)
        if not alarm:
            logger.info(f"Alarm {alarm_id} not found at timer start.")
            return
        seconds_to_wait = time_left(alarm["end_time"])
        if seconds_to_wait > 0:
            await asyncio.sleep(seconds_to_wait)
        alarm["status"] = "finished"
        logger.info(f"Alarm {alarm_id} for {alarm['egg_type']} egg finished at {datetime.utcnow().isoformat()}")
        # TODO: Implement real notification logic here (push notification, email, etc.)
    except Exception as e:
        logger.exception(e)

@dataclass
class AlarmRequest:
    egg_type: str

@dataclass
class CancelRequest:
    alarm_id: str

@app.route("/api/alarm/set", methods=["POST"])
# workaround: validate_request must be last for POST due to quart-schema defect
@validate_request(AlarmRequest)
async def set_alarm(data: AlarmRequest):
    egg_type = data.egg_type
    if egg_type not in EGG_COOK_TIMES:
        return jsonify({"status": "error", "message": "Invalid egg_type"}), 400

    if active_alarm:
        active_alarm.clear()

    alarm_id = str(uuid.uuid4())
    duration = EGG_COOK_TIMES[egg_type]
    end_time = datetime.utcnow() + timedelta(seconds=duration)

    active_alarm[alarm_id] = {
        "egg_type": egg_type,
        "end_time": end_time,
        "status": "active",
    }

    asyncio.create_task(alarm_timer(alarm_id))

    return jsonify({
        "status": "success",
        "message": f"Alarm set for {egg_type}-boiled egg",
        "alarm_id": alarm_id,
        "duration_seconds": duration,
    })

@app.route("/api/alarm/status", methods=["GET"])
async def get_alarm_status():
    if not active_alarm:
        return jsonify({
            "alarm_id": None,
            "egg_type": None,
            "time_left_seconds": 0,
            "status": "none",
        })

    alarm_id, alarm = next(iter(active_alarm.items()))
    status = alarm["status"]
    left = time_left(alarm["end_time"]) if status == "active" else 0

    return jsonify({
        "alarm_id": alarm_id,
        "egg_type": alarm["egg_type"],
        "time_left_seconds": left,
        "status": status,
    })

@app.route("/api/alarm/cancel", methods=["POST"])
# workaround: validate_request must be last for POST due to quart-schema defect
@validate_request(CancelRequest)
async def cancel_alarm(data: CancelRequest):
    alarm_id = data.alarm_id
    if not alarm_id or alarm_id not in active_alarm:
        return jsonify({
            "status": "error",
            "message": "Invalid or unknown alarm_id"
        }), 400

    active_alarm.clear()
    # TODO: If integrated with a real scheduler/task manager, cancel the task here

    return jsonify({
        "status": "success",
        "message": "Alarm cancelled"
    })

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)