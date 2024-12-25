import logging
from common.app_init import entity_service, connections
from common.config.config import ENTITY_VERSION

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def ingest_data(meta, data):
    logger.info("Starting data ingestion process.")
    try:
        code = data["request_parameters"]["code"]
        country = data["request_parameters"]["country"]
        name = data["request_parameters"]["name"]
        # Call the external API to retrieve data
        raw_data = connections.ingest_data(code, country, name)
        # Save the raw data to the raw_data_entity
        raw_data_entity_data = {
            "brpCode": raw_data.get("brpCode"),
            "brpName": raw_data.get("brpName"),
            "country": raw_data.get("country"),
            "businessId": raw_data.get("businessId"),
            "codingScheme": raw_data.get("codingScheme"),
            "validityStart": raw_data.get("validityStart"),
            "validityEnd": raw_data.get("validityEnd"),
        }
        entity_service.add_item(
            meta["token"], "raw_data_entity", ENTITY_VERSION, raw_data_entity_data
        )
        logger.info("Data ingestion complete. Raw data saved successfully.")
    except Exception as e:
        logger.error(f"Error during data ingestion: {e}")
        raise
