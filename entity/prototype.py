from dataclasses import dataclass
import asyncio
import logging
from datetime import datetime, timedelta, time
from typing import Dict, Optional
import uuid

from quart import Quart, jsonify
from quart_schema import QuartSchema, validate_request
import httpx

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

alarms: Dict[str, Dict] = {}
EGG_COOK_TIMES = {"soft": 4, "medium": 7, "hard": 12}

@dataclass
class AlarmRequest:
    egg_type: str
    custom_time: Optional[str]

@dataclass
class DeleteRequest:
    alarm_id: str

async def fetch_external_time_api():
    try:
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
    alarm = alarms.get(alarm_id)
    if not alarm:
        logger.warning(f"Alarm {alarm_id} not found for triggering")
        return
    now = datetime.utcnow()
    wait_seconds = (alarm["set_time"] - now).total_seconds()
    if wait_seconds > 0:
        await asyncio.sleep(wait_seconds)
    logger.info(f"Alarm triggered: {alarm_id} for {alarm['egg_type']} egg at {alarm['set_time'].isoformat()}")
    alarm["status"] = "triggered"
    # TODO: Extend to send real notification

async def process_alarm_creation(data: dict):
    egg_type = data.get("egg_type")
    custom_time_str = data.get("custom_time")
    if egg_type not in EGG_COOK_TIMES:
        raise ValueError("Invalid egg_type")
    current_utc = await fetch_external_time_api()
    if custom_time_str:
        hour, minute = map(int, custom_time_str.split(":"))
        alarm_time_candidate = datetime.combine(current_utc.date(), time(hour, minute))
        if alarm_time_candidate <= current_utc:
            alarm_time_candidate += timedelta(days=1)
        alarm_time = alarm_time_candidate
    else:
        alarm_time = current_utc + timedelta(minutes=EGG_COOK_TIMES[egg_type])
    alarm_id = str(uuid.uuid4())
    alarm_data = {
        "alarm_id": alarm_id,
        "egg_type": egg_type,
        "set_time": alarm_time,
        "status": "created",
        "requested_at": current_utc,
    }
    alarms[alarm_id] = alarm_data
    asyncio.create_task(alarm_trigger(alarm_id))
    return alarm_data

@app.route("/alarm", methods=["POST"])
@validate_request(AlarmRequest)  # Workaround: route first and validation last for POST due to quart-schema defect
async def set_alarm(data: AlarmRequest):
    try:
        alarm_data = await process_alarm_creation(data.__dict__)
        return jsonify({
            "alarm_id": alarm_data["alarm_id"],
            "set_time": alarm_data["set_time"].isoformat(),
            "egg_type": alarm_data["egg_type"],
            "status": alarm_data["status"]
        }), 201
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": str(e)}), 400

@app.route("/alarms", methods=["GET"])
async def get_alarms():
    active_alarms = []
    now = datetime.utcnow()
    for alarm in alarms.values():
        if alarm["status"] != "triggered" and alarm["set_time"] > now:
            active_alarms.append({
                "alarm_id": alarm["alarm_id"],
                "set_time": alarm["set_time"].isoformat(),
                "egg_type": alarm["egg_type"],
                "status": "active"
            })
    return jsonify(active_alarms), 200

@app.route("/alarm/delete", methods=["POST"])
@validate_request(DeleteRequest)  # Workaround: route first and validation last for POST due to quart-schema defect
async def delete_alarm(data: DeleteRequest):
    try:
        alarm_id = data.alarm_id
        if alarm_id not in alarms:
            return jsonify({"error": "Alarm not found"}), 404
        alarms[alarm_id]["status"] = "deleted"
        # TODO: Optionally cancel pending alarm trigger task
        return jsonify({"alarm_id": alarm_id, "status": "deleted"}), 200
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": str(e)}), 400

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)