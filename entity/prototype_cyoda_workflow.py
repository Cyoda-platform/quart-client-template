Understood. We should move as much async logic as possible from the endpoints into dedicated `process_{entity_name}` workflow functions which are invoked automatically right before entity persistence on `add_item`. This aligns with the design you described: workflow functions get the entity dict, can modify it, and can add supplementary entities of other models but **must not** add/update/delete the same entity model to avoid recursion.

---

### What can be moved into workflow functions?

1. **`process_alert`**:  
   Endpoint logic in `/alerts` POST that sets default `"status": "active"` and maybe any normalization or validation that can be done just before persistence.

2. **`process_weather_processing_jobs`**:  
   The logic that sets the job status to `"processing"`, triggers the async alert evaluation and notification sending, and finally updates job status to `"completed"` or `"failed"` — this is currently in the `process_weather_data` async task started by the endpoint.  
   This entire async processing logic fits *perfectly* into the `process_weather_processing_jobs` workflow function, because the workflow supports async code and runs just before persistence.  
   
   Since the workflow function cannot update the same entity (to avoid recursion), the solution is:  
   - Modify the incoming job entity's state directly (e.g. update `status`, timestamps)  
   - For updating the job status later (e.g. `"completed"` after processing), we can use `entity_service.update_item` since it's a different call and different entity model. The entity model is the same (`weather_processing_jobs`), so we must be careful. But per your instructions, updating the same entity model inside workflow will cause infinite recursion.  
   
   So the workaround:  
   - We **cannot** call `add_item/update_item/delete_item` on the same entity model inside the workflow function.  
   - But the workflow runs *before* persistence of the new entity. So we can modify the entity in-place for the initial status `"processing"`.  
   - For the final status updates, we can spawn a separate background task outside workflow or in workflow but via other means (e.g. external worker), but this contradicts your requirement to move everything into workflow.  
   
   Possible approach:  
   - In the workflow, immediately set entity status `"processing"` and fire off a background `asyncio.create_task` that runs the evaluation and notification sending, and upon completion updates the job entity (via `update_item`) — this is **allowed** since the background task is outside the main workflow call stack.  
   - Because the workflow function itself does not call `update_item` on the same entity synchronously, no recursion.  
   
   So, move all processing logic into `process_weather_processing_jobs`, spawn background task inside it to do async tasks and update job status.

3. **`process_notifications_history`**:  
   The notification sending is currently in `evaluate_alerts_for_weather_data`. Since notifications_history entities are created in that function, and it calls `add_item` with `workflow=None`.  
   We can create a `process_notifications_history` workflow function to handle additional processing (e.g. logging, enrichment, retries).  
   
   But since the sending is done *before* persistence of notifications_history, moving sending itself into the workflow is problematic (it would delay persistence). However, per your requirement that async tasks should be moved into workflows, we can:
   - Move the sending logic into `process_notifications_history` workflow function.  
   - That means the `add_item` call for notifications_history will trigger sending notification *before* persistence.  
   - This is acceptable if the notification sending must happen synchronously before persistence. Otherwise, we can fire & forget inside workflow.  
   
   So the best design is:  
   - Keep notification sending inside workflow function `process_notifications_history`.  
   - From other workflows or business code, just add notifications_history entities with workflow=process_notifications_history and no sending logic there.  
   
4. **`process_alert`**:  
   Currently has minimal logic; keep it for normalization and validation.

---

### Implementation plan:

- Move alert creation logic into `process_alert` (e.g. set status `"active"` if missing).
- Move weather job processing into `process_weather_processing_jobs`:
  - Set `"processing"` status.
  - Spawn background task to evaluate alerts, send notifications, and update job status.
- Move notification sending into `process_notifications_history`.
- Simplify endpoint code to just call `add_item` with appropriate workflow, no extra async logic.
- Ensure we never call `add/update/delete` on the same entity model inside its workflow synchronously.
- Use background tasks inside workflow functions if needed.

---

### Updated code with workflows and simplified endpoints

```python
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request
import asyncio
import logging
from datetime import datetime, timezone
from uuid import uuid4
import httpx

from app_init.app_init import BeanFactory
from common.config.config import ENTITY_VERSION

factory = BeanFactory(config={'CHAT_REPOSITORY': 'cyoda'})
entity_service = factory.get_services()['entity_service']
cyoda_auth_service = factory.get_services()["cyoda_auth_service"]

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

@dataclass
class Condition:
    type: str
    operator: str
    value: Any

@dataclass
class NotificationTargets:
    email: Optional[str] = None
    sms: Optional[str] = None
    webhook: Optional[str] = None

@dataclass
class CreateAlertRequest:
    user_id: str
    name: str
    conditions: List[Condition]
    notification_channels: List[str]
    notification_targets: NotificationTargets

@dataclass
class UpdateAlertRequest:
    name: Optional[str] = None
    conditions: Optional[List[Condition]] = None
    notification_channels: Optional[List[str]] = None
    notification_targets: Optional[NotificationTargets] = None

@dataclass
class WeatherDataRequest:
    location: str
    timestamp: str
    temperature: float
    rain_forecast: bool
    additional_data: Optional[Dict[str, Any]] = None

# -----------------------
# Workflow functions
# -----------------------

async def process_alert(entity: Dict[str, Any]) -> None:
    """
    Workflow for 'alert' entity:
    Set default status, normalize fields etc.
    """
    if "status" not in entity:
        entity["status"] = "active"
    if "alert_id" not in entity:
        entity["alert_id"] = str(uuid4())
    # Normalize status to lowercase
    if "status" in entity and isinstance(entity["status"], str):
        entity["status"] = entity["status"].lower()
    # Could add more normalization here

async def process_notifications_history(entity: Dict[str, Any]) -> None:
    """
    Workflow for 'notifications_history':
    Send the actual notification asynchronously before persisting.
    """
    user_id = entity.get("user_id")
    alert_id = entity.get("alert_id")
    channel = entity.get("channel")
    status = entity.get("status")  # We can ignore or update based on sending result
    if not all([user_id, alert_id, channel]):
        logger.warning("Missing fields for notifications_history entity, skipping send")
        return

    # Determine target from entity if stored, else can't send
    # We have no direct notification_targets here; assume stored or passed in entity.
    # For demonstration, we assume entity has 'target' field.
    target = entity.get("target")
    if not target:
        logger.warning("No target found in notifications_history entity, skipping send")
        return

    message = entity.get("message", f"Alert {alert_id} triggered")

    try:
        logger.info(f"Sending notification via {channel} to {target} for user {user_id}")
        if channel == "webhook":
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(target, json={"alert_id": alert_id, "message": message})
                if resp.status_code >= 400:
                    logger.warning(f"Webhook notification failed: {resp.status_code} {resp.text}")
                    entity["status"] = "failed"
                else:
                    entity["status"] = "sent"
        else:
            # For email, sms, etc. just simulate send success
            entity["status"] = "sent"
    except Exception as e:
        logger.exception(f"Failed to send notification: {e}")
        entity["status"] = "failed"

async def process_weather_processing_jobs(entity: Dict[str, Any]) -> None:
    """
    Workflow for 'weather_processing_jobs':
    Set status to processing, spawn background task to evaluate alerts and update job status.
    """
    if "status" not in entity or entity["status"] == "queued":
        entity["status"] = "processing"

    # Spawn background task to do actual processing to avoid blocking persistence
    async def background_job(job_entity: Dict[str, Any]):
        job_id = job_entity.get("job_id")
        if not job_id:
            logger.error("Job entity missing job_id. Cannot process.")
            return
        location = job_entity.get("location")
        timestamp = job_entity.get("timestamp")
        temperature = job_entity.get("temperature")
        rain_forecast = job_entity.get("rain_forecast")

        try:
            alerts_triggered = []
            # Fetch active alerts
            active_alerts = await entity_service.get_items_by_condition(
                token=cyoda_auth_service,
                entity_model="alert",
                entity_version=ENTITY_VERSION,
                condition={"status": "active"}
            )
            for alert in active_alerts:
                user_id = alert.get("user_id")
                if user_id is None:
                    logger.warning(f"Alert missing user_id: {alert}")
                    continue
                conditions = alert.get("conditions", [])
                matches = True
                for cond in conditions:
                    ctype = cond.get("type")
                    op = cond.get("operator")
                    value = cond.get("value")
                    if ctype == "temperature":
                        try:
                            val = float(value)
                            if op == "gt" and not (temperature > val):
                                matches = False
                            elif op == "lt" and not (temperature < val):
                                matches = False
                            elif op == "eq" and not (temperature == val):
                                matches = False
                        except Exception as e:
                            logger.warning(f"Invalid temperature condition in alert {alert.get('alert_id')}: {e}")
                            matches = False
                    elif ctype == "rain_forecast":
                        val_bool = (str(value).lower() == "true")
                        if op == "eq" and rain_forecast != val_bool:
                            matches = False
                    else:
                        logger.warning(f"Unknown condition type: {ctype}")
                        matches = False
                    if not matches:
                        break

                if not matches:
                    continue

                notification_channels = alert.get("notification_channels", [])
                notification_targets = alert.get("notification_targets", {})
                alert_id = alert.get("alert_id")
                notification_results = []

                for channel in notification_channels:
                    target = None
                    if isinstance(notification_targets, dict):
                        target = notification_targets.get(channel)
                    elif isinstance(notification_targets, NotificationTargets):
                        target = getattr(notification_targets, channel, None)
                    if not target:
                        logger.warning(f"Missing notification target for channel {channel} in alert {alert_id}")
                        continue
                    message = f"Weather alert triggered for your rule '{alert.get('name')}' at {location}."

                    # Create notifications_history entity; notification sending happens in its workflow
                    notification_entity = {
                        "notification_id": str(uuid4()),
                        "alert_id": alert_id,
                        "channel": channel,
                        "status": "pending",  # set pending, workflow will send and update
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "user_id": user_id,
                        "target": target,
                        "message": message
                    }
                    try:
                        await entity_service.add_item(
                            token=cyoda_auth_service,
                            entity_model="notifications_history",
                            entity_version=ENTITY_VERSION,
                            entity=notification_entity,
                            workflow=process_notifications_history
                        )
                        notification_results.append({"channel": channel, "status": "sent"})
                    except Exception as e:
                        logger.exception(f"Failed to add notifications_history entity: {e}")
                        notification_results.append({"channel": channel, "status": "failed"})

                alerts_triggered.append({
                    "alert_id": alert_id,
                    "user_id": user_id,
                    "notification_channels": [r["channel"] for r in notification_results],
                    "notification_status": "sent" if all(r["status"] == "sent" for r in notification_results) else "failed"
                })

            # Update weather_processing_jobs entity status to completed
            jobs = await entity_service.get_items_by_condition(
                token=cyoda_auth_service,
                entity_model="weather_processing_jobs",
                entity_version=ENTITY_VERSION,
                condition={"job_id": job_id}
            )
            if jobs:
                technical_id = jobs[0].get("technical_id")
                if technical_id:
                    await entity_service.update_item(
                        token=cyoda_auth_service,
                        entity_model="weather_processing_jobs",
                        entity_version=ENTITY_VERSION,
                        entity={
                            "status": "completed",
                            "alerts_triggered": alerts_triggered,
                            "processed_at": datetime.now(timezone.utc).isoformat()
                        },
                        technical_id=technical_id,
                        meta={}
                    )
        except Exception as exc:
            logger.exception(f"Exception in background job processing weather data: {exc}")
            # Update job status to failed
            try:
                jobs = await entity_service.get_items_by_condition(
                    token=cyoda_auth_service,
                    entity_model="weather_processing_jobs",
                    entity_version=ENTITY_VERSION,
                    condition={"job_id": job_id}
                )
                if jobs:
                    technical_id = jobs[0].get("technical_id")
                    if technical_id:
                        await entity_service.update_item(
                            token=cyoda_auth_service,
                            entity_model="weather_processing_jobs",
                            entity_version=ENTITY_VERSION,
                            entity={
                                "status": "failed",
                                "error": str(exc),
                                "processed_at": datetime.now(timezone.utc).isoformat()
                            },
                            technical_id=technical_id,
                            meta={}
                        )
            except Exception as e2:
                logger.exception(f"Failed to update weather_processing_jobs to failed: {e2}")

    # Fire and forget background task
    asyncio.create_task(background_job(entity.copy()))

# -----------------------
# Endpoint handlers (simplified)
# -----------------------

@app.route("/alerts", methods=["POST"])
@validate_request(CreateAlertRequest)
async def create_alert(data: CreateAlertRequest):
    try:
        alert_obj = {
            "user_id": data.user_id,
            "name": data.name,
            "conditions": [cond.__dict__ for cond in data.conditions],
            "notification_channels": data.notification_channels,
            "notification_targets": data.notification_targets.__dict__ if data.notification_targets else {},
            # "status" and "alert_id" set in workflow
        }
        await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model="alert",
            entity_version=ENTITY_VERSION,
            entity=alert_obj,
            workflow=process_alert
        )
        return jsonify({"alert_id": alert_obj.get("alert_id"), "status": "active"}), 201
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to create alert"}), 500

@app.route("/alerts/<alert_id>", methods=["POST"])
@validate_request(UpdateAlertRequest)
async def update_alert(data: UpdateAlertRequest, alert_id):
    try:
        alerts = await entity_service.get_items_by_condition(
            token=cyoda_auth_service,
            entity_model="alert",
            entity_version=ENTITY_VERSION,
            condition={"alert_id": alert_id}
        )
        if not alerts:
            return jsonify({"error": "Alert not found"}), 404
        alert_entity = alerts[0]
        technical_id = alert_entity.get("technical_id")
        if technical_id is None:
            return jsonify({"error": "Alert technical ID missing"}), 500
        updated = {}
        if data.name is not None:
            updated["name"] = data.name
        if data.conditions is not None:
            updated["conditions"] = [cond.__dict__ for cond in data.conditions]
        if data.notification_channels is not None:
            updated["notification_channels"] = data.notification_channels
        if data.notification_targets is not None:
            updated["notification_targets"] = data.notification_targets.__dict__
        if not updated:
            return jsonify({"alert_id": alert_id, "status": "updated"}), 200
        alert_entity.update(updated)
        await entity_service.update_item(
            token=cyoda_auth_service,
            entity_model="alert",
            entity_version=ENTITY_VERSION,
            entity=alert_entity,
            technical_id=technical_id,
            meta={}
        )
        return jsonify({"alert_id": alert_id, "status": "updated"}), 200
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to update alert"}), 500

@app.route("/alerts/<alert_id>/delete", methods=["POST"])
async def delete_alert(alert_id):
    try:
        alerts = await entity_service.get_items_by_condition(
            token=cyoda_auth_service,
            entity_model="alert",
            entity_version=ENTITY_VERSION,
            condition={"alert_id": alert_id}
        )
        if not alerts:
            return jsonify({"error": "Alert not found"}), 404
        alert_entity = alerts[0]
        technical_id = alert_entity.get("technical_id")
        if technical_id is None:
            return jsonify({"error": "Alert technical ID missing"}), 500
        alert_entity["status"] = "deleted"
        await entity_service.update_item(
            token=cyoda_auth_service,
            entity_model="alert",
            entity_version=ENTITY_VERSION,
            entity=alert_entity,
            technical_id=technical_id,
            meta={}
        )
        return jsonify({"alert_id": alert_id, "status": "deleted"}), 200
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to delete alert"}), 500

@app.route("/users/<user_id>/alerts", methods=["GET"])
async def get_user_alerts(user_id):
    try:
        alerts = await entity_service.get_items_by_condition(
            token=cyoda_auth_service,
            entity_model="alert",
            entity_version=ENTITY_VERSION,
            condition={"user_id": user_id}
        )
        return jsonify(alerts), 200
    except Exception as e:
        logger.exception(e)
        return jsonify([]), 200

@app.route("/weather/data", methods=["POST"])
@validate_request(WeatherDataRequest)
async def post_weather_data(data: WeatherDataRequest):
    try:
        job_id = str(uuid4())
        requested_at = datetime.now(timezone.utc).isoformat()
        job_entity = {
            "job_id": job_id,
            "status": "queued",
            "requestedAt": requested_at,
            "location": data.location,
            "timestamp": data.timestamp,
            "temperature": data.temperature,
            "rain_forecast": data.rain_forecast,
            "additional_data": data.additional_data or {}
        }
        await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model="weather_processing_jobs",
            entity_version=ENTITY_VERSION,
            entity=job_entity,
            workflow=process_weather_processing_jobs
        )
        return jsonify({"job_id": job_id, "status": "queued", "requestedAt": requested_at}), 200
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to process weather data"}), 500

@app.route("/users/<user_id>/notifications", methods=["GET"])
async def get_notifications(user_id):
    try:
        notifications = await entity_service.get_items_by_condition(
            token=cyoda_auth_service,
            entity_model="notifications_history",
            entity_version=ENTITY_VERSION,
            condition={"user_id": user_id}
        )
        return jsonify(notifications), 200
    except Exception as e:
        logger.exception(e)
        return jsonify([]), 200

if __name__ == '__main__':
    import sys
    logging.basicConfig(
        stream=sys.stdout,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        level=logging.INFO,
    )
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
```

---

### Explanation:

- **Endpoints now only prepare data and call `add_item()` or `update_item()`**.
- **`process_alert`** sets default fields and normalizes the alert before persistence.
- **`process_weather_processing_jobs`** sets status to processing and immediately spawns a background task to do alert evaluation and notification creation.
  - Background task uses `entity_service` to fetch alerts and add notification entities with workflow `process_notifications_history`.
  - Background task updates the job status once done or on failure.
- **`process_notifications_history`** sends the notification and updates the notification entity status accordingly before persistence.
- No workflow calls `add/update/delete` on its own entity model synchronously — avoiding infinite recursion.
- All async logic and fire-and-forget tasks moved into workflows, making controllers slim and robust.

---

If you want me to further break down workflows or add tests/examples, just ask!