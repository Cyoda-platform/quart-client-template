async def start_processing(entity: dict):
    entity["status"] = "started"
    entity["workflowProcessed"] = False

async def prepare_data(entity: dict):
    # Example: prepare data before API call
    entity["prepared_data"] = {"key": "value"}  # replace with actual preparation logic
    entity["status"] = "data_prepared"

async def call_external_api(entity: dict):
    # Example: simulate external API call
    import asyncio
    await asyncio.sleep(1)  # simulate network delay
    # simulate response
    entity["api_response"] = {"success": True, "data": {"id": 123, "result": "ok"}}
    entity["status"] = "api_called"

async def handle_api_response(entity: dict):
    response = entity.get("api_response", {})
    if response.get("success"):
        entity["processed_data"] = response.get("data")
    else:
        entity["processed_data"] = None
    entity["status"] = "response_handled"

async def is_response_successful(entity: dict) -> bool:
    response = entity.get("api_response", {})
    return response.get("success", False)

async def is_response_failure(entity: dict) -> bool:
    response = entity.get("api_response", {})
    return not response.get("success", False)

async def handle_api_error(entity: dict):
    # Example: simple retry logic or mark error
    retries = entity.get("retries", 0)
    if retries < 3:
        entity["retries"] = retries + 1
        entity["status"] = "retrying"
    else:
        entity["status"] = "failed"
        entity["error"] = "API call failed after retries"

async def finalize_processing(entity: dict):
    if entity.get("status") == "failed":
        entity["workflowProcessed"] = False
    else:
        entity["workflowProcessed"] = True
        entity["status"] = "completed"