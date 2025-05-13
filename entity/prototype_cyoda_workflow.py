Understood. The key points are:

- Move as much logic as possible from the endpoints and async background tasks into the workflow functions (`process_pet`, etc.).
- These workflow functions are invoked asynchronously before persistence and can modify the entity in place.
- They can also perform other entity operations *on different entity_models*, but cannot modify the same entity_model to avoid infinite recursion.
- This approach will simplify controllers — they will mainly validate and forward data to `entity_service.add/update/delete` with proper workflow functions.
- For update and delete, since these don't have a `workflow` parameter (based on your initial snippet), we need to check if they support it. If not, move related logic to workflow function for add only or adapt accordingly.

---

### Plan

- For **Add** (`add_item`), move all logic from the async task (`process_add_pet`) into the workflow function `process_pet`.
  - The endpoint creates the entity dictionary with minimal data.
  - The workflow enriches the entity, e.g. sets `processed` flag, timestamps, and any other logic (like adding related entities).
- For **Update** and **Delete**, since `entity_service.update_item` and `delete_item` do not seem to support `workflow`, keep async tasks but minimize logic; we can move validations or enrichments before calling update/delete in the async function.
- For **Search**, since it's a read operation, it can't be a workflow (workflow is for persistence). Keep the async task but move composing condition logic out of endpoint into a helper or into a dedicated "search workflow" function (though that won't be a workflow for persistence, just refactor for clarity).

---

### Implementation

- Refactor `process_add_pet` to only call `entity_service.add_item` with minimal entity data + `workflow=process_pet`.
- Implement `process_pet` workflow function to perform all enrichment, validation, and related entity additions.
- Refactor update/delete async tasks to minimal logic with validation.
- Refactor search async task to helper function outside endpoint.

---

### Updated code snippet focused on the changes

```python
# Workflow function for pet entity add
async def process_pet(entity: Dict[str, Any]) -> Dict[str, Any]:
    """
    Workflow function applied to pet entity asynchronously before persistence.
    This is the right place to put all enrichment, validation, related entity additions, etc.
    """
    # Example enrichment:
    entity["processed"] = True
    entity["processedAt"] = datetime.utcnow().isoformat()

    # You can add logic here to add related entities of other models,
    # e.g. logging, history, notifications, etc.

    # Example: If the pet type requires a related entity, create it here:
    # await entity_service.add_item(token=cyoda_auth_service, entity_model="pet_history", entity_version=ENTITY_VERSION, entity={"pet_id": entity.get("id"), "event": "added"})

    # Note: Do NOT call add/update/delete on the same entity_model 'pet' here, only modify "entity" dict.
    return entity


async def process_add_pet(data: Dict[str, Any], job_id: str) -> None:
    """
    Async task to submit add pet job.
    The actual enrichment and processing is in process_pet workflow.
    """
    try:
        # Minimal entity to add - keep simple, enrich in workflow
        payload = {
            "name": data.get("name"),
            "photoUrls": data.get("photoUrls", []),
            "status": data.get("status"),
            "category": {"name": data.get("type")} if data.get("type") else None,
        }
        if payload["category"] is None:
            payload.pop("category")

        pet_id = await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model=PET_ENTITY_NAME,
            entity_version=ENTITY_VERSION,
            entity=payload,
            workflow=process_pet
        )

        entity_jobs[job_id].update({
            "status": "completed",
            "result": {"id": str(pet_id), "message": "Pet add job submitted"},
            "completedAt": datetime.utcnow().isoformat()
        })
    except Exception as e:
        logger.exception("Error adding pet")
        entity_jobs[job_id].update({
            "status": "failed",
            "error": str(e)
        })

# For update and delete, keep logic minimal; no workflow supported (assumed)
async def process_update_pet(data: Dict[str, Any], job_id: str) -> None:
    try:
        pet_id = data.get("id")
        if not pet_id:
            raise ValueError("Pet id is required for update")

        payload = {
            "name": data.get("name"),
            "photoUrls": data.get("photoUrls", []),
            "status": data.get("status"),
            "category": {"name": data.get("type")} if data.get("type") else None,
        }
        # Remove None values
        payload = {k: v for k, v in payload.items() if v is not None}
        if "category" in payload and payload["category"] is None:
            payload.pop("category")

        # No workflow param assumed here
        await entity_service.update_item(
            token=cyoda_auth_service,
            entity_model=PET_ENTITY_NAME,
            entity_version=ENTITY_VERSION,
            entity=payload,
            technical_id=str(pet_id),
            meta={}
        )
        entity_jobs[job_id].update({
            "status": "completed",
            "result": {"message": "Pet update job submitted"},
            "completedAt": datetime.utcnow().isoformat()
        })
    except Exception as e:
        logger.exception("Error updating pet")
        entity_jobs[job_id].update({
            "status": "failed",
            "error": str(e)
        })


async def process_delete_pet(data: Dict[str, Any], job_id: str) -> None:
    try:
        pet_id = data.get("id")
        if not pet_id:
            raise ValueError("Pet id is required for delete")

        # No workflow param assumed here
        await entity_service.delete_item(
            token=cyoda_auth_service,
            entity_model=PET_ENTITY_NAME,
            entity_version=ENTITY_VERSION,
            technical_id=str(pet_id),
            meta={}
        )
        entity_jobs[job_id].update({
            "status": "completed",
            "result": {"message": "Pet delete job submitted"},
            "completedAt": datetime.utcnow().isoformat()
        })
    except Exception as e:
        logger.exception("Error deleting pet")
        entity_jobs[job_id].update({
            "status": "failed",
            "error": str(e)
        })


# Refactor search processing to a helper function, no workflow possible (read only)
async def process_search(criteria: Dict[str, Any]) -> None:
    job_id = criteria.get("job_id")
    try:
        conditions = []
        if criteria.get("status"):
            conditions.append({
                "jsonPath": "$.status",
                "operatorType": "EQUALS",
                "value": criteria["status"],
                "type": "simple"
            })
        if criteria.get("type"):
            conditions.append({
                "jsonPath": "$.category.name",
                "operatorType": "IEQUALS",
                "value": criteria["type"],
                "type": "simple"
            })
        if criteria.get("name"):
            conditions.append({
                "jsonPath": "$.name",
                "operatorType": "ICONTAINS",
                "value": criteria["name"],
                "type": "simple"
            })

        condition = {
            "cyoda": {
                "type": "group",
                "operator": "AND",
                "conditions": conditions
            }
        } if conditions else None

        if condition:
            pets = await entity_service.get_items_by_condition(
                token=cyoda_auth_service,
                entity_model=PET_ENTITY_NAME,
                entity_version=ENTITY_VERSION,
                condition=condition
            )
        else:
            pets = await entity_service.get_items(
                token=cyoda_auth_service,
                entity_model=PET_ENTITY_NAME,
                entity_version=ENTITY_VERSION,
            )

        entity_jobs[job_id].update({
            "status": "completed",
            "result": {"pets": pets},
            "completedAt": datetime.utcnow().isoformat()
        })
    except Exception as e:
        logger.exception("Error processing pet search")
        entity_jobs[job_id].update({
            "status": "failed",
            "error": str(e)
        })
```

---

### Summary:

- All enrichment, validation, and side effects that can be done before persistence on the "add" entity are moved to `process_pet` workflow function.
- The async task `process_add_pet` now only packages minimal data and calls `add_item` with the workflow.
- Update and delete tasks remain but are minimal, as they cannot use `workflow`.
- Search processing logic is moved out of endpoint to a helper async function but cannot be a workflow because it's a read operation.
- Endpoints become very thin: validate, create job entry, start async task.

---

If you want, I can provide the **full updated code** with all endpoints refactored accordingly. Would you like that?