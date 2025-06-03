Understood. The key is to shift as much logic as possible from the Quart endpoint handlers into the async workflow functions `process_alarm` (or other entities if any). The workflow function is called just before the entity is persisted. It can modify the current entity (directly) and can add or get other entities (with different entity_models), but cannot add/update/delete the same entity_model (to avoid infinite loops).

Also, the workflow function supports async code, so `asyncio.create_task` or similar fire-and-forget async logic should be moved there.

---

### What we currently have:

- `process_alarm_creation` builds the initial `alarm_data` dict and calls `entity_service.add_item` with workflow=`process_alarm`.
- `process_alarm` is currently a stub that just normalizes the `status` field.
- `alarm_trigger` calls a sleep until the alarm time, then updates the alarm status to "triggered".
- The endpoint `/alarm` calls `process_alarm_creation` and returns the response.
- The endpoint `/alarm/delete` marks the alarm as deleted (updates the entity).
- The endpoint `/alarms` returns active alarms (read-only).

---

### What can be moved into `process_alarm` workflow?

- The firing of the async task for `alarm_trigger` (currently in `process_alarm_creation`) can be moved into `process_alarm`.
- Any state initialization for the entity (e.g. setting status) can be done inside the workflow function.
- The calculation of `set_time` cannot be done inside the workflow since `custom_time` and `egg_type` come from the request, and entity is created only after that; but it can be moved if we pass partial data to `add_item`.
  
Actually, the calculation of `set_time` is business logic based on the input data (`egg_type` and optionally `custom_time`) and current time — so it can be moved into the workflow, if we store `egg_type` and `custom_time` in the entity passed to `add_item` and do the final `set_time` computation in the workflow.

This is a good approach: the controller only passes the raw data, the workflow does all the computations, sets final state, and schedules async trigger.

---

### Plan:

- The endpoint `/alarm` just passes the validated data as entity to `entity_service.add_item` with workflow=`process_alarm`.
- `process_alarm`:
  - calculates `set_time` (using `egg_type` and `custom_time` fields)
  - sets the `status` to `"created"`
  - sets `requested_at` to current time
  - schedules the async task `alarm_trigger` with the assigned entity id (which we cannot get inside the workflow, but maybe the workflow runs before persistence, so we don't have the id yet?)
  
---

**Important point:** The workflow runs *before* persistence, so the entity ID is not yet assigned. The workflow function receives the entity dict **without** the assigned technical ID.

Because the `alarm_trigger` async task requires the entity ID, and the ID is only returned by `add_item` call, we cannot start the async task inside the workflow function directly.

**How to solve this?**

- We can store the alarm data with the workflow function.
- After `add_item` returns the new entity ID, we can start the async task using that ID.
- So the async task start cannot be moved inside the workflow function unless we can somehow get the entity ID.

---

**Conclusion:**

- Move all logic that does not require the entity ID — calculations, field setting, status, timestamps — into the workflow.
- Leave the async task launch (which requires entity ID) in the controller after the `add_item` call.
- The controller simply calls `add_item` with minimal logic, then launches the async task for alarm trigger.

---

**For other endpoints:**

- `/alarm/delete`: sets status to `"deleted"` — no workflow here, because it is an update, not add. Could we move that to a workflow on update? The new API might support a workflow for update as well? Your prompt doesn't mention that. So we keep as is.

- `/alarms`: purely query, no change.

---

### Updated code reflecting these rules:

```python
from dataclasses import dataclass
import asyncio
import logging
from datetime import datetime, timedelta, time
from typing import Optional

from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request
import httpx

from app_init.app_init import BeanFactory
from common.config.config import ENTITY_VERSION

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

factory = BeanFactory(config={'CHAT_REPOSITORY': 'cyoda'})
entity_service = factory.get_services()['entity_service']
cyoda_auth_service = factory.get_services()["cyoda_auth_service"]

app = Quart(__name__)
QuartSchema(app)

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


async def process_alarm(entity: dict):
    """
    Workflow function for the 'alarm' entity.
    This function can modify the entity or add/get other entities before persistence.
    """
    # Validate egg_type
    egg_type = entity.get("egg_type")
    if egg_type not in EGG_COOK_TIMES:
        raise ValueError(f"Invalid egg_type: {egg_type}")

    # Get current time (UTC) from external source or fallback to utcnow
    current_utc = await fetch_external_time_api()

    # Determine set_time
    custom_time_str = entity.get("custom_time")
    if custom_time_str:
        try:
            hour, minute = map(int, custom_time_str.split(":"))
            alarm_time_candidate = datetime.combine(current_utc.date(), time(hour, minute))
            if alarm_time_candidate <= current_utc:
                alarm_time_candidate += timedelta(days=1)
            set_time = alarm_time_candidate
        except Exception:
            raise ValueError("Invalid custom_time format, expected HH:MM")
    else:
        set_time = current_utc + timedelta(minutes=EGG_COOK_TIMES[egg_type])

    entity["set_time"] = set_time.isoformat()
    entity["status"] = "created"
    entity["requested_at"] = current_utc.isoformat()

    # Remove custom_time from entity as it's only input param
    if "custom_time" in entity:
        del entity["custom_time"]

    # Normalize status to lowercase (extra safety)
    entity["status"] = entity["status"].lower()

    # Other workflow logic can be added here, e.g. logging, adding secondary entities, etc.

    return entity


@app.route("/alarm", methods=["POST"])
@validate_request(AlarmRequest)
async def set_alarm(data: AlarmRequest):
    try:
        # Pass raw data as entity with workflow; the workflow will do all processing
        entity_dict = data.__dict__
        alarm_id = await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model=ENTITY_NAME,
            entity_version=ENTITY_VERSION,
            entity=entity_dict,
            workflow=process_alarm
        )

        # Launch async alarm trigger task after persistence with ID
        asyncio.create_task(alarm_trigger(alarm_id))

        # Retrieve the alarm entity to return full data including set_time, status
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


@app.route("/alarms", methods=["GET"])
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
            if alarm.get("status") != "triggered" and alarm.get("status") != "deleted":
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


@app.route("/alarm/delete", methods=["POST"])
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
        # TODO: Optionally cancel pending alarm trigger task
        return jsonify({"alarm_id": alarm_id, "status": "deleted"}), 200
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": str(e)}), 400


if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
```

---

### Summary:
- All entity state and validation logic moved into `process_alarm` workflow function.
- The controller `/alarm` endpoint calls `add_item` with minimal logic and passes workflow.
- The async task to trigger alarm is still launched in controller after persistence (since we need the ID).
- Other endpoints stay mostly as before.
- This approach clearly separates business logic into the workflow, making controllers very thin and robust.
- The workflow can be extended further with multi-entity logic if needed.

---

If you want, I can help you refactor update/delete workflows similarly if your backend supports it. Otherwise, this is the recommended pattern for add/create operations.