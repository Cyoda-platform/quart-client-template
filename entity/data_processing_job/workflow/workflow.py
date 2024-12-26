import logging
from common.app_init import entity_service
from common.service.raw_data_ingestion import ingest_data
from common.service.trino_service import get_trino_schema_id_by_entity_name
from common.ai.ai_assistant_service import IAiAssistantService
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def ingest_data_process(meta, data):
    logger.info("Starting data ingestion process.")
    # Call the existing ingest_data function to retrieve raw data
    raw_data = ingest_data(
        code=data["request_parameters"]["code"],
        country=data["request_parameters"]["country"],
        name=data["request_parameters"]["name"],
    )

    # Save the raw data to raw_data_entity
    raw_data_entity_id = entity_service.add_item(
        meta["token"], "raw_data_entity", "1.0", raw_data
    )
    logger.info(f"Raw data ingested and saved with ID: {raw_data_entity_id}")


def aggregate_raw_data(meta, data):
    logger.info("Starting aggregation process.")
    # Here we would implement logic to aggregate the raw data
    # For this example, we will assume that the aggregation logic is implemented elsewhere
    aggregation_result = {}  # Placeholder for aggregation logic
    aggregated_data_entity_id = entity_service.add_item(
        meta["token"], "aggregated_data_entity", "1.0", aggregation_result
    )
    logger.info(f"Aggregated data saved with ID: {aggregated_data_entity_id}")


def generate_report_process(meta, data):
    logger.info("Generating report.")
    # Generate a report based on the aggregated data
    report_data = {
        "report_id": "report_001",
        "content": "This is a report based on the aggregated data.",
    }
    report_entity_id = entity_service.add_item(
        meta["token"], "report_entity", "1.0", report_data
    )
    logger.info(f"Report generated and saved with ID: {report_entity_id}")


# Unit tests for the processor functions
class TestDataProcessingJob:
    def test_ingest_data_process(self):
        # Mock the entity_service.add_item method and other dependencies
        pass  # Implement test logic here

    def test_aggregate_raw_data(self):
        # Mock dependencies and implement test logic
        pass

    def test_generate_report_process(self):
        # Mock dependencies and implement test logic
        pass
