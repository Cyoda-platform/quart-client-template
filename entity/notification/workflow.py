async def set_openai_api_key(entity: dict):
    entity["OPENAI_API_KEY"] = "test"
    entity["workflowProcessed"] = True