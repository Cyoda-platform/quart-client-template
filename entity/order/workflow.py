from datetime import datetime
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

async def process_order(entity: Dict[str, Any]):
    entity.setdefault('createdAt', datetime.utcnow().isoformat())
    entity['orderStatus'] = 'processing'
    await process_place_order(entity)
    await process_finalize_order(entity)

async def process_place_order(entity: Dict[str, Any]):
    petstore_response = await place_order_petstore(entity)
    if "error" in petstore_response:
        entity['orderStatus'] = 'failed'
        entity['failureReason'] = petstore_response['error']
        logger.error(f"Failed to place order id={entity.get('id')}: {petstore_response['error']}")
    else:
        entity['orderStatus'] = 'completed'
        entity['petstoreOrderId'] = petstore_response.get('id')
        entity['completedAt'] = datetime.utcnow().isoformat()

async def process_finalize_order(entity: Dict[str, Any]):
    # TODO: Add any finalization logic if needed
    pass