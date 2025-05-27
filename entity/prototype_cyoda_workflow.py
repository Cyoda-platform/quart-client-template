Understood. The goal is to move as much logic as possible from the endpoints into the corresponding workflow functions (`process_subscriber`, `process_game`), which are called asynchronously just before persisting the entity. This will clean up the controller code and ensure that related async background tasks or entity modifications are encapsulated in workflow functions.

---

### Key points & constraints:

- Workflow function receives the entity data dict as the only argument.
- Workflow can modify the entity state **directly** (e.g. `entity['attribute'] = value`).
- Workflow can also **add/get** entities of **different** entity_model via `entity_service` async methods.
- Workflow **cannot** add/update/delete entities of the **same** entity_model (would cause recursion).
- Workflow can run async code, including fire-and-forget tasks.
- All logic related to entity processing, enrichment, side-effects (like notifications) should be moved to workflow functions.
- Controllers should only handle request validation and minimal orchestration like triggering the add_item with workflow.

---

### What to move?

- For `subscriber` entity:
  - Normalizing the email to lowercase (already done).
  - Fire-and-forget sending notification emails? But email sending is currently done in `_send_notifications` after fetching games, so maybe not here.
  - The subscription endpoint currently just saves the subscriber — no extra async work needed.

- For `game` entity:
  - Currently, after fetching games, the app deletes old games and adds new games with workflow.
  - The `_fetch_process_and_notify` function:
    - deletes old games for the date
    - add new games (with workflow)
    - calls `_send_notifications` to notify subscribers asynchronously.
  - The notification sending is logically tied to the arrival of new games.
  - We **cannot** delete games inside `process_game` workflow because that would be the same entity_model (game).
  - But we **can** move the notification sending into the workflow for games because it relates to new games being persisted.
  - However, the workflow runs per game entity, so sending notifications per game is inefficient and repetitive.
  - Alternative: create a new entity to represent the "fetch job" or "game batch" to trigger notification sending once.
  - Since we currently do not have such a batch entity, and the workflow runs per entity, best to move notification sending out of endpoint and into the workflow of `game` entity but only for the first game of the batch or when a special flag exists.

**Given the constraints and the current code, the best approach is:**

- Move **email normalization** and any subscriber-specific preprocessing into `process_subscriber`.
- Move **status normalization** etc. into `process_game`.
- Move the **notification sending** logic into `process_game` workflow but ensure it is only triggered once per batch, to avoid repeated sends per game entity.
- The deletion of old games must remain in the endpoint (or helper before adding new games), since deleting the same entity_model in workflow is forbidden.
- The fetch endpoint just triggers fetching and adding games (with workflows).
- The notification sending is moved **inside** the `process_game` workflow but guarded so it runs once per batch.

---

### Implementation Notes

To run notification sending once per batch in `process_game`, we can:

- Use a shared in-memory flag or cache keyed by date to ensure notifications are only sent once per batch.
- Or, better: inside workflow, check if notification for the date has been sent; if not, send and mark as sent.

This is safe since workflows are async and can call entity_service to get subscribers.

---

### Updated code with these changes

```python
# ... [imports and other unchanged code above]

import asyncio

# In-memory cache to track notification sending per date (in production replace with persistent cache)
_notification_sent_for_date = set()

# Workflow function for subscriber entity
async def process_subscriber(entity: Dict) -> None:
    """
    Workflow function applied to subscriber entity before persistence.
    Normalize email to lowercase.
    """
    email = entity.get("email")
    if email:
        entity["email"] = email.strip().lower()


# Workflow function for game entity
async def process_game(entity: Dict) -> None:
    """
    Workflow function applied to game entity before persistence.
    Normalize status field and send notifications once per date.
    """
    status = entity.get("Status")
    if status:
        entity["Status"] = status.upper()

    # Send notifications once per date after first game entity processed
    date_str = entity.get("Day")
    if not date_str:
        return

    # Avoid duplicate notifications sending
    if date_str in _notification_sent_for_date:
        return

    _notification_sent_for_date.add(date_str)

    # Fire-and-forget notification sending
    asyncio.create_task(_send_notifications_for_date(date_str))


async def _send_notifications_for_date(date_str: str):
    try:
        # Load all games for date
        condition = {
            "cyoda": {
                "type": "group",
                "operator": "AND",
                "conditions": [
                    {
                        "jsonPath": "$.Day",
                        "operatorType": "EQUALS",
                        "value": date_str,
                        "type": "simple"
                    }
                ]
            }
        }
        games = await entity_service.get_items_by_condition(
            token=cyoda_auth_service,
            entity_model="game",
            entity_version=ENTITY_VERSION,
            condition=condition
        )
        if not games:
            return

        subs = await entity_service.get_items(
            token=cyoda_auth_service,
            entity_model="subscriber",
            entity_version=ENTITY_VERSION
        )
        if not subs:
            logger.info("No subscribers to notify.")
            return

        for sub in subs:
            email = sub.get("email")
            nt = sub.get("notificationType", "summary")
            if not email:
                continue
            content = _build_email_content(date_str, games, nt)
            # TODO: Implement real email sending
            logger.info(f"Sending {nt} email to {email} for {date_str}")
            await asyncio.sleep(0.1)  # simulate sending
    except Exception:
        logger.exception("Failed to send notifications")

# -- Controller / endpoint functions --

@app.route("/subscribe", methods=["POST"])
@validate_request(SubscribeRequest)
async def subscribe(data: SubscribeRequest):
    try:
        email = data.email
        notification_type = data.notificationType
        if notification_type not in ("summary", "full"):
            return jsonify({"error": "Invalid notificationType"}), 400

        subscriber_data = {"email": email, "notificationType": notification_type}

        condition = {
            "cyoda": {
                "type": "group",
                "operator": "AND",
                "conditions": [
                    {
                        "jsonPath": "$.email",
                        "operatorType": "EQUALS",
                        "value": email,
                        "type": "simple"
                    }
                ]
            }
        }
        existing_subs = await entity_service.get_items_by_condition(
            token=cyoda_auth_service,
            entity_model="subscriber",
            entity_version=ENTITY_VERSION,
            condition=condition
        )
        if existing_subs:
            existing_id = existing_subs[0].get("technical_id") or existing_subs[0].get("id") or existing_subs[0].get("email")
            await entity_service.update_item(
                token=cyoda_auth_service,
                entity_model="subscriber",
                entity_version=ENTITY_VERSION,
                entity=subscriber_data,
                technical_id=str(existing_id),
                meta={}
            )
        else:
            await entity_service.add_item(
                token=cyoda_auth_service,
                entity_model="subscriber",
                entity_version=ENTITY_VERSION,
                entity=subscriber_data,
                workflow=process_subscriber
            )

        logger.info(f"New subscription: {email} with preference {notification_type}")
        return jsonify({
            "message": "Subscription successful",
            "email": email,
            "notificationType": notification_type
        })
    except Exception:
        logger.exception("Failed to subscribe")
        return jsonify({"error": "Failed to subscribe"}), 500

@app.route("/games/fetch", methods=["POST"])
@validate_request(FetchRequest)
async def fetch_and_store_games(data: FetchRequest):
    try:
        date_str = data.date
        try:
            datetime.datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            return jsonify({"error": "Date must be in YYYY-MM-DD format"}), 400

        asyncio.create_task(_fetch_process(date_str))
        return jsonify({
            "message": "Scores fetch started",
            "date": date_str
        })
    except Exception:
        logger.exception("Failed to trigger fetch")
        return jsonify({"error": "Failed to trigger fetch"}), 500

async def _fetch_process(date_str: str):
    try:
        url = NBA_API_URL.format(date=date_str, key=API_KEY)
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            games = resp.json()
            logger.info(f"Fetched {len(games)} games for {date_str}")

        # Delete old games for the date (cannot do in workflow)
        condition = {
            "cyoda": {
                "type": "group",
                "operator": "AND",
                "conditions": [
                    {
                        "jsonPath": "$.Day",
                        "operatorType": "EQUALS",
                        "value": date_str,
                        "type": "simple"
                    }
                ]
            }
        }
        old_games = await entity_service.get_items_by_condition(
            token=cyoda_auth_service,
            entity_model="game",
            entity_version=ENTITY_VERSION,
            condition=condition
        )
        for old_game in old_games:
            old_id = old_game.get("technical_id") or old_game.get("id")
            if old_id:
                await entity_service.delete_item(
                    token=cyoda_auth_service,
                    entity_model="game",
                    entity_version=ENTITY_VERSION,
                    technical_id=str(old_id),
                    meta={}
                )

        # Add new games with workflow
        for game in games:
            await entity_service.add_item(
                token=cyoda_auth_service,
                entity_model="game",
                entity_version=ENTITY_VERSION,
                entity=game,
                workflow=process_game
            )
    except Exception:
        logger.exception("Failed during fetch process")

# --- other unchanged endpoints ---

# rest of the code remains the same, including _build_email_content, scheduler, etc.
```

---

### Summary of what was moved:

- Email normalization logic moved to `process_subscriber`.
- Game status normalization moved to `process_game`.
- Notification sending moved into a **single** async fire-and-forget task inside `process_game` workflow, guarded to only run once per date.
- Fetch endpoint now only fetches, deletes old games, and adds new ones with workflow, no notification logic.
- Subscription endpoint only adds/updates subscribers with workflow.

---

If you want, I can provide the entire updated file again or just the diff. This approach keeps controllers thin and moves async side-effects and enrichment into workflows as you requested. Let me know if you want me to do that!