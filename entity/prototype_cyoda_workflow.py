Absolutely, moving the async logic from the endpoint/controller into the `process_{entity_name}` workflow functions is a best practice that will:

- Keep your controllers thin and focused on HTTP request/response handling.
- Encapsulate business logic related to entity state transformation and side effects in one place.
- Make your codebase more robust, maintainable, and easier to test.
- Enable direct asynchronous workflows right before persistence.

---

### How to proceed:

1. Identify all async logic currently running in the endpoint related to the entity.
2. Move that logic into the workflow function `process_{entity_name}`.
3. Within this workflow function:
   - Modify the entity state directly on the passed-in data dict.
   - Perform any async calls for other entities (add/get) but **do not update/add/delete the current entity model** to avoid recursion.
4. Return the modified entity data from the workflow function — it will be persisted automatically after the workflow completes.

---

### Example Refactor

Let's say you have an endpoint like this (pseudocode):

```python
@router.post("/sample-entity")
async def create_sample_entity(data: SampleEntityCreateSchema, cyoda_auth_service=Depends(get_auth)):
    # Some async task
    await some_async_side_effect(data)
    
    # Adding supplementary entity
    related_id = await entity_service.add_item(
        token=cyoda_auth_service,
        entity_model="related_entity",
        entity_version=ENTITY_VERSION,
        entity={"parent_id": data.id, "info": "extra"},
        workflow=process_related_entity
    )
    
    # Mutate data before persistence
    data['processed'] = False
    
    entity_id = await entity_service.add_item(
        token=cyoda_auth_service,
        entity_model="sample_entity",
        entity_version=ENTITY_VERSION,
        entity=data,
        workflow=None  # no workflow used yet
    )
    return {"id": entity_id}
```

---

### Refactor by moving async logic into workflow:

```python
ENTITY_VERSION = "1.0"

async def process_sample_entity(entity):
    # Perform async side effect
    await some_async_side_effect(entity)
    
    # Add supplementary entity asynchronously
    related_entity_data = {
        "parent_id": entity.get("id"),
        "info": "extra"
    }
    # Note: adding a different entity model is allowed
    related_id = await entity_service.add_item(
        token=cyoda_auth_service,  # this must be accessible here or passed in context
        entity_model="related_entity",
        entity_version=ENTITY_VERSION,
        entity=related_entity_data,
        workflow=process_related_entity
    )
    
    # Update current entity state directly
    entity['processed'] = True
    
    # Return mutated entity (optional, but good practice)
    return entity

# Endpoint becomes very lean:
@router.post("/sample-entity")
async def create_sample_entity(data: SampleEntityCreateSchema, cyoda_auth_service=Depends(get_auth)):
    entity_id = await entity_service.add_item(
        token=cyoda_auth_service,
        entity_model="sample_entity",
        entity_version=ENTITY_VERSION,
        entity=data,
        workflow=process_sample_entity
    )
    return {"id": entity_id}
```

---

### Important considerations:
- You’ll need to ensure that dependencies like `cyoda_auth_service` token are accessible inside your workflow functions.
- One approach is to pass required context (like auth token) into the workflow function via partial application or closure.
- Alternatively, you can design workflow functions as factory functions that accept the token and return the actual async workflow.

---

### Example workflow function factory to pass token:

```python
def make_process_sample_entity(token):
    async def process_sample_entity(entity):
        await some_async_side_effect(entity)
        
        related_entity_data = {
            "parent_id": entity.get("id"),
            "info": "extra"
        }
        await entity_service.add_item(
            token=token,
            entity_model="related_entity",
            entity_version=ENTITY_VERSION,
            entity=related_entity_data,
            workflow=process_related_entity
        )
        
        entity['processed'] = True
        return entity
    return process_sample_entity

# Usage in endpoint:
@router.post("/sample-entity")
async def create_sample_entity(data: SampleEntityCreateSchema, cyoda_auth_service=Depends(get_auth)):
    workflow = make_process_sample_entity(cyoda_auth_service)
    entity_id = await entity_service.add_item(
        token=cyoda_auth_service,
        entity_model="sample_entity",
        entity_version=ENTITY_VERSION,
        entity=data,
        workflow=workflow
    )
    return {"id": entity_id}
```

---

### Summary:
- Move all async side effects, supplementary entity additions, state mutations into `process_{entity_name}` workflow.
- Workflow receives the entity dict, modifies it, can do async calls for other models/entities.
- Do NOT add/update/delete current entity model inside workflow (only mutate entity dict).
- Pass necessary context (auth tokens, etc.) to workflow via closures or other means.
- Keep endpoint/controller logic minimal: just call `entity_service.add_item` with workflow.

---

If you share your current endpoint code, I can help you refactor it fully into this pattern. Would you like me to do that?