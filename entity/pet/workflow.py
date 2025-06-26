import logging
from datetime import datetime

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

async def process_mark_processed(entity: dict):
    entity["processedAt"] = datetime.utcnow().isoformat()
    entity["workflowProcessed"] = True
    logger.info(f"process_mark_processed: marked pet '{entity.get('name')}' as processed")

async def process_fetch_external_data(entity: dict):
    if entity.get("needsFetch"):
        entity["externalDataFetched"] = True
        logger.info(f"process_fetch_external_data: fetched external data for pet '{entity.get('name')}'")

async def process_fetch_external_data_condition(entity: dict) -> bool:
    return entity.get("externalDataFetched", False)

async def process_skip_enrich_condition(entity: dict) -> bool:
    return not entity.get("externalDataFetched", False)

async def process_enrich_data(entity: dict):
    if entity.get("externalDataFetched"):
        entity["enriched"] = True
        logger.info(f"process_enrich_data: enriched pet '{entity.get('name')}' data")

async def process_finalize(entity: dict):
    entity["finalizedAt"] = datetime.utcnow().isoformat()
    logger.info(f"process_finalize: finalized pet '{entity.get('name')}' processing")