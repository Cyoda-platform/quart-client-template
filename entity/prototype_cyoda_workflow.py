Understood. Your approach to refactor async logic from endpoints into dedicated workflow functions named `process_{entity_name}` is a good one. It will help in achieving separation of concerns, keep controllers thin, and make the codebase more maintainable and robust.

### Summary of your approach and constraints:
- Move any async logic from endpoint handlers into `process_{entity_name}` functions.
- These functions are invoked asynchronously before persisting the entity.
- The workflow function takes the entity data as the only argument.
- You can modify the entity state directly by updating its dictionary keys.
- You can fetch and add secondary/supplementary/raw data entities of different models.
- You **cannot** call `entity_service.add/update/delete` on the current entity inside the workflow.
- The workflow supports async code, so all async tasks, including fire-and-forget, should be moved here.
- This refactor is required and the correct approach.

---

### General approach to refactor:

1. **Identify all async code inside controllers/endpoints that relate to entity processing.**  
   This includes:
   - Async calls that fetch or enrich entity data before saving.
   - Fire and forget async tasks triggered after receiving data.
   - Validation or enrichment that involves async calls.

2. **Create a new `process_{entity_name}` function for each entity**  
   - The function signature:  
     ```python
     async def process_{entity_name}(entity: dict):
     ```
   - Inside this function, move all async logic that modifies or enriches the entity before persistence.
   - Modify the entity dict directly if needed.

3. **Update the endpoints/controllers**  
   - Remove the async logic moved to workflow functions.
   - Call the workflow function asynchronously before calling persistence (`add`/`update`).
   - Await the workflow function to complete before persisting.

4. **Keep any calls to `entity_service.add/update/delete` outside the workflow function**  
   - As per the requirement, do not call these inside workflow.
   - The persistence call happens after the workflow function completes.

---

### Example

Suppose you have an entity `user` and an endpoint like this:

```python
@router.post("/users")
async def create_user(request: Request):
    user_data = await request.json()
    # Async enrichment before saving
    user_data['profile'] = await async_fetch_profile(user_data['id'])
    await entity_service.add('user', user_data)
    return {"status": "created"}
```

Refactor to:

```python
async def process_user(entity: dict):
    # Move async enrichment here
    entity['profile'] = await async_fetch_profile(entity['id'])


@router.post("/users")
async def create_user(request: Request):
    user_data = await request.json()
    await process_user(user_data)
    await entity_service.add('user', user_data)
    return {"status": "created"}
```

---

### Checklist for your codebase

- [ ] Identify all async enrichment or processing logic in controllers.
- [ ] Create `process_{entity_name}` functions.
- [ ] Move async logic into `process_{entity_name}`.
- [ ] Modify entity dict in workflow function directly.
- [ ] Remove async logic from controllers.
- [ ] Call and await workflow function before persistence.
- [ ] Avoid calling entity_service add/update/delete inside workflow.
- [ ] Test that entity state updates as expected after workflow.

---

If you want, you can share specific code snippets/endpoints, and I can help convert them to this new workflow pattern. Otherwise, this guidance should help you refactor your codebase properly.

---

**In summary:**  
Yes, it is the right approach and required. All async logic should be moved into `process_{entity_name}` workflow functions invoked before persistence. This will make controllers slimmer and code more robust. Let me know if you want me to assist with actual code refactoring.