```python
import asyncio
import logging
from datetime import datetime, timedelta, time
from typing import Dict, Optional
import uuid

from quart import Quart, request, jsonify
from quart_schema import QuartSchema
import httpx

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# In-memory async-safe cache for alarms: {alarm_id: alarm_data}
alarms: Dict[str, Dict] = {}

# Typical boiling durations in minutes
EGG_COOK_TIMES = {
    "soft": 4,
    "medium": 7,
    "hard": 12
}


async def fetch_external_time_api():
    """
    Example real API usage: Fetch current UTC time from a public time API.
    Using httpx.AsyncClient to get current UTC time (ISO8601).
    """
    try:
        async with httpx.AsyncClient() as client:
            # WorldTimeAPI returns JSON with datetime field
            r = await client.get("http://worldtimeapi.org/api/timezone/Etc/UTC")
            r.raise_for_status()
            data = r.json()
            current_time_iso = data.get("utc_datetime")
            return datetime.fromisoformat(current_time_iso.replace("Z", "+00:00"))
    except Exception as e:
        logger.exception("Failed to fetch current time from external API")
        # Fallback to local UTC time if API fails
        return datetime.utcnow()


async def alarm_trigger(alarm_id: str):
    """
    Coroutine that waits until alarm time and then "triggers" the alarm.
    """
    alarm = alarms.get(alarm_id)
    if not alarm:
        logger.warning(f"Alarm {alarm_id} not found for triggering")
        return

    now = datetime.utcnow()
    wait_seconds = (alarm["set_time"] - now).total_seconds()
    if wait_seconds > 0:
        await asyncio.sleep(wait_seconds)

    # Trigger the alarm notification (here we just log it)
    logger.info(f"Alarm triggered: {alarm_id} for {alarm['egg_type']} egg at {alarm['set_time'].isoformat()}")

    # Update alarm status to triggered
    alarm["status"] = "triggered"

    # TODO: Extend to send real notification (push, email, etc.)


async def process_alarm_creation(data: dict):
    """
    Process alarm creation:
    - Calculate alarm time if custom_time is None
    - Store alarm in async-safe dict
    - Fire and forget alarm trigger coroutine
    """
    egg_type = data.get("egg_type")
    custom_time_str = data.get("custom_time")  # format "HH:MM" or None

    if egg_type not in EGG_COOK_TIMES:
        raise ValueError("Invalid egg_type")

    # Fetch current UTC time from an external API
    current_utc = await fetch_external_time_api()

    if custom_time_str:
        try:
            hour, minute = map(int, custom_time_str.split(":"))
            # Construct alarm datetime for today or tomorrow if time passed
            alarm_time_candidate = datetime.combine(current_utc.date(), time(hour, minute))
            if alarm_time_candidate <= current_utc:
                alarm_time_candidate += timedelta(days=1)
            alarm_time = alarm_time_candidate
        except Exception:
            raise ValueError("Invalid custom_time format, expected HH:MM")
    else:
        # Automatic alarm time = current time + egg cooking duration (minutes)
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

    # Fire and forget the alarm trigger task
    asyncio.create_task(alarm_trigger(alarm_id))

    return alarm_data


@app.route("/alarm", methods=["POST"])
async def set_alarm():
    try:
        data = await request.get_json(force=True)
        alarm_data = await process_alarm_creation(data)
        response = {
            "alarm_id": alarm_data["alarm_id"],
            "set_time": alarm_data["set_time"].isoformat(),
            "egg_type": alarm_data["egg_type"],
            "status": alarm_data["status"]
        }
        return jsonify(response), 201
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": str(e)}), 400


@app.route("/alarms", methods=["GET"])
async def get_alarms():
    # Return list of active alarms only (status != triggered)
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
async def delete_alarm():
    try:
        data = await request.get_json(force=True)
        alarm_id = data.get("alarm_id")
        if not alarm_id or alarm_id not in alarms:
            return jsonify({"error": "Alarm not found"}), 404

        # Mark alarm as deleted (soft delete)
        alarms[alarm_id]["status"] = "deleted"
        # TODO: Optionally cancel pending alarm trigger task if tracked

        return jsonify({"alarm_id": alarm_id, "status": "deleted"}), 200
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": str(e)}), 400


if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
```
