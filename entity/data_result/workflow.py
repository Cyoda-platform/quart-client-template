import datetime
import asyncio
import logging

from common.config.config import ENTITY_VERSION  # always use this constant
from app_init.app_init import entity_service, cyoda_token
from common.repository.cyoda.cyoda_init import init_cyoda

# External API URLs (constants)
BRANDS_API_URL = "https://api.practicesoftwaretesting.com/brands"
CATEGORIES_API_URL = "https://api.practicesoftwaretesting.com/categories"

logger = logging.getLogger(__name__)

async def process_add_supplementary_info(entity):
    # Adds supplementary data as a separate entity. This is a fire-and-forget task.
    try:
        supplementary_data = {
            "original_combined_at": entity.get("combined_at"),
            "note": "Supplementary information added asynchronously",
            "supplementary_at": datetime.datetime.utcnow().isoformat() + "Z"
        }
        await entity_service.add_item(
            token=cyoda_token,
            entity_model="supplementary_data",
            entity_version=ENTITY_VERSION,
            entity=supplementary_data,
            workflow=lambda e: e  # No additional workflow logic for supplementary data.
        )
        logger.info("Supplementary information added successfully.")
    except Exception as e:
        # Log but do not propagate to avoid affecting the main workflow.
        logger.error(f"Error adding supplementary info: {str(e)}")

def process_add_timestamp(entity):
    # Adds a processed timestamp directly to the entity.
    entity["processed_at"] = datetime.datetime.utcnow().isoformat() + "Z"