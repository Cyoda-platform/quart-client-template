Understood. The goal is to move all the asynchronous business logic currently in the endpoints (especially fire-and-forget tasks or any pre/post-processing) into the workflow functions `process_{entity_name}`. This will make the controllers lean, and the workflows will handle all entity modifications and related async calls before persistence.

Key considerations:
- Workflow functions receive the entity data dict as their only argument.
- They can modify that dict directly; changes will be persisted automatically.
- They can call entity_service to get/add entities of different models but **cannot** add/update/delete the same entity model (to avoid infinite recursion).
- Fire-and-forget async tasks (like sending messages or further processing) should be triggered inside the workflow functions instead of the endpoints.

---

### What to move:

1. **Trade entity**

   - Currently:  
     - Endpoint calls `entity_service.add_item` with workflow `process_trade` (which we implemented with some logic).  
     - Then it fires `asyncio.create_task(process_trade_task(trade_data))` to do further processing (update trade with state transitions, rejections, etc).  
   
   - Task:  
     Move **all** the async logic including state transitions, legal entity existence check, etc into the workflow `process_trade`.  
     Remove the fire-and-forget `process_trade_task` call from the endpoint.  
     The workflow function will do everything needed before persistence and will persist the final state.

2. **Legal entity**

   - Currently:  
     - Workflow `process_legal_entity` just sets updatedAt timestamp.  
     - No async fire-and-forget tasks.  
   
   - Task:  
     No change, just keep the workflow as is.

3. **DTCC Message entity**

   - Currently:  
     - Endpoint adds dtcc_message with workflow `process_dtcc_message` (which sets status and createdAt).  
     - Then fires `asyncio.create_task(process_dtcc_message_task(dtcc_id))` which simulates sending the message and updates it.  
   
   - Task:  
     Move the entire sending logic (simulate delay, update status, append history) into the workflow `process_dtcc_message`.  
     Workflow can launch async fire-and-forget helper tasks internally (allowed), or await internally.  
     Since the workflow function itself is called before persistence, and is async, the entire sending simulation can be done there.  
     This means no fire-and-forget call from the endpoint.

4. **DTCC message resend endpoint**

   - This endpoint currently updates the entity and then fires the `process_dtcc_message_task` again.  
   - This is updating an existing entity, so per rules, we **cannot** call add/update/delete on the same entity_model inside workflow.  
   - The resend endpoint is a direct update - so we keep that update code in endpoint, but can we move the fire-and-forget task into the workflow?  
   - No, because this is an update, not an add. The workflow function is only called on add.  
   - So for resend, we have to keep the fire-and-forget call in the endpoint, or refactor the resend logic to first update then add a new entity (which is not desirable).  
   - So keep the resend fire-and-forget as is.

---

### Implementation plan:

- **process_trade:**  
  Do all validation, legal entity check, trade state transitions inside. Remove `process_trade_task` entirely.  
  The endpoint just adds the item with workflow, returns immediately.

- **process_dtcc_message:**  
  Implement full send simulation inside workflow function. Remove `process_dtcc_message_task`.

- **Remove all `asyncio.create_task(...)` calls from endpoints except for resend endpoint** (because resend triggers an update).

---

### Updated code (only changed parts shown for brevity):

```python
# Remove the old async tasks from outside or mark as unused
# async def process_trade_task(...)  # removed completely
# async def process_dtcc_message_task(...)  # removed completely

# Updated workflow functions

async def process_trade(trade_data: dict):
    """
    Full trade processing before persistence:
    - Check legal entity existence
    - Transition trade state
    - Set rejection reason if needed
    """
    try:
        lei = trade_data.get("counterpartyLEI")
        if not await check_legal_entity_exists(lei):
            trade_data["status"] = "rejected"
            trade_data["rejectionReason"] = f"Unknown legal entity LEI: {lei}"
        else:
            event_type = trade_data.get("eventType", "execution")
            # Get existing trade if any to check current state
            existing_trade = await entity_service.get_item(
                token=cyoda_auth_service,
                entity_model="trade",
                entity_version=ENTITY_VERSION,
                technical_id=trade_data.get("tradeId")
            ) or {}
            # Transition state based on event type
            transition_trade_state(existing_trade or trade_data, event_type)
        trade_data["lastProcessedAt"] = utc_now_iso()
    except Exception as e:
        logger.exception(f"Error in process_trade workflow: {e}")

async def process_dtcc_message(dtcc_data: dict):
    """
    Full DTCC message sending simulation before persistence:
    - Add status, createdAt if missing
    - Simulate sending delay
    - Update status to sent or failed accordingly
    - Append to history
    """
    if "status" not in dtcc_data:
        dtcc_data["status"] = "readyToSend"
    if "createdAt" not in dtcc_data:
        dtcc_data["createdAt"] = utc_now_iso()
    dtcc_id = dtcc_data.get("dtccMessageId")
    try:
        # Simulate sending delay
        await asyncio.sleep(1)
        dtcc_data["status"] = "sent"
        dtcc_data["sentAt"] = utc_now_iso()
        dtcc_data.setdefault("history", []).append({
            "timestamp": utc_now_iso(),
            "event": "sent",
            "details": "Mock DTCC message sent successfully",
        })
    except Exception as e:
        dtcc_data["status"] = "failed"
        dtcc_data.setdefault("history", []).append({
            "timestamp": utc_now_iso(),
            "event": "failed",
            "details": str(e),
        })
        logger.exception(f"Error sending DTCC message {dtcc_id}: {e}")

# Update endpoint handlers

@app.route("/trades/fpml", methods=["POST"])
@validate_request(Fpml_trade_request)
async def post_fpml_trade(data: Fpml_trade_request):
    try:
        if not await validate_fpml(data.fpmlMessage, data.signature):
            return jsonify({"message": "FpML validation failed"}), 400
        if not await verify_message_source():
            return jsonify({"message": "Message source authentication failed"}), 401
        trade_data = await parse_fpml(data.fpmlMessage)
        trade_data["status"] = "draft"
        trade_data["createdAt"] = utc_now_iso()
        trade_id_resp = await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model="trade",
            entity_version=ENTITY_VERSION,
            entity=trade_data,
            workflow=process_trade
        )
        # Removed asyncio.create_task(process_trade_task(trade_data))
        return jsonify({
            "tradeId": str(trade_id_resp),
            "status": trade_data["status"],
            "message": "Trade received and processed",
        })
    except Exception as e:
        logger.exception(e)
        return jsonify({"message": "Internal server error"}), 500

@app.route("/dtcc/messages", methods=["POST"])
@validate_request(Dtcc_message_request)
async def post_dtcc_message(data: Dtcc_message_request):
    try:
        # Check that tradeId exists
        trade_item = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model="trade",
            entity_version=ENTITY_VERSION,
            technical_id=data.tradeId
        )
        if not trade_item:
            return jsonify({"message": f"Unknown tradeId {data.tradeId}"}), 400
        if data.messageType not in {"new", "modify", "cancel"}:
            return jsonify({"message": "Invalid messageType"}), 400
        dtcc_id = str(uuid.uuid4())
        dtcc_data = {
            "dtccMessageId": dtcc_id,
            "tradeId": data.tradeId,
            "messageType": data.messageType,
            "history": [],
        }
        await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model="dtcc_message",
            entity_version=ENTITY_VERSION,
            entity=dtcc_data,
            workflow=process_dtcc_message
        )
        # Removed asyncio.create_task(process_dtcc_message_task(dtcc_id))
        return jsonify({
            "dtccMessageId": dtcc_id,
            "status": "readyToSend",
            "message": "DTCC message generated and sent",
        })
    except Exception as e:
        logger.exception(e)
        return jsonify({"message": "Internal server error"}), 500

# The resend endpoint stays as is because it updates existing entity and triggers fire-and-forget update task

```

---

### Explanation:

- The trade processing logic is now fully synchronous inside the async workflow. We eagerly check legal entity existence, transition states, and set rejection if needed.

- The dtcc_message workflow simulates sending the message with delay before persistence, updating status and history accordingly.

- The endpoints no longer call fire-and-forget tasks for processing or sending; these are handled completely inside workflows.

- The resend endpoint remains responsible for updating dtcc_message status and launching the send task because workflows do not run on updates.

---

If you want, I can provide the full updated code with all changes applied. Would you like me to do that?