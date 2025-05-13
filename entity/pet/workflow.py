async def process_order(entity: dict):
    await process_initialize(entity)
    await process_place_order(entity)
    await process_finalize(entity)

async def process_initialize(entity: dict):
    from datetime import datetime
    entity.setdefault('createdAt', datetime.utcnow().isoformat())
    entity['orderStatus'] = 'processing'

async def process_place_order(entity: dict):
    petstore_response = await place_order_petstore(entity)
    if "error" in petstore_response:
        entity['orderStatus'] = 'failed'
        entity['failureReason'] = petstore_response['error']
    else:
        entity['orderStatus'] = 'completed'
        entity['petstoreOrderId'] = petstore_response.get('id')
        from datetime import datetime
        entity['completedAt'] = datetime.utcnow().isoformat()

async def process_finalize(entity: dict):
    # Placeholder for any finalization logic
    pass