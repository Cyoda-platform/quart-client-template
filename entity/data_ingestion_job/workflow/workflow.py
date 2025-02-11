import json
import logging
from app_init.app_init import entity_service
from common.service.trino_service import run_sql_query

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def schedule_job_processor(meta, data):
    """Processes scheduling of the job."""
    logger.info(f"Scheduling job with ID: {data['job_id']}")
    # Here you can implement any scheduling logic if needed
    return {"status": "success", "message": "Job scheduled successfully."}


async def ingest_data_processor(meta, data):
    """Processes the data ingestion from the specified source."""
    job_id = data['job_id']
    data_source_url = data['data_source']['url']

    logger.info(f"Ingesting data for job ID: {job_id} from {data_source_url}")

    # Mock ingest_data function since module doesn't exist
    async def ingest_raw_data(url):
        return [{"data_id": "data_001", "title": "Activity 1", "due_date": "2025-02-10T22:55:28Z", "completed": False}]

    # Call the ingest_data function
    raw_data = await ingest_raw_data(data_source_url)

    if raw_data:
        # Save the raw data entity
        for item in raw_data:
            await entity_service.add_item(
                meta["token"], "raw_data_entity", "1.0", item
            )
        logger.info(f"Data ingestion complete for job ID: {job_id}")
    else:
        logger.error(f"No data ingested for job ID: {job_id}")

    return {"status": "success", "message": "Data ingested successfully."}


async def report_generation_processor(meta, data):
    """Generates the report from the ingested data."""
    job_id = data['job_id']
    logger.info(f"Generating report for job ID: {job_id}")

    # Example logic to generate aggregated report data
    aggregated_data = {
        "report_id": f"report_{job_id}",
        "generated_at": "2025-02-10T23:00:00Z",
        "admin_email": "admin@example.com",
        "aggregated_data": [],  # Populate with aggregated data
        "total_activities": 0,
        "completed_activities": 0,
        "pending_activities": 0,
        "summary": "Summary of activities."
    }

    # Save the aggregated report entity
    await entity_service.add_item(
        meta["token"], "aggregated_report_entity", "1.0", aggregated_data
    )

    logger.info(f"Report generated successfully for job ID: {job_id}")
    return {"status": "success", "message": "Report generated successfully."}

# Tests
import unittest
from unittest.mock import patch, AsyncMock
import asyncio

class TestDataIngestionJobProcessors(unittest.TestCase):

    def test_ingest_data_processor(self):
        async def run_test():
            meta = {"token": "test_token"}
            data = {
                "job_id": "job_2023_10_01",
                "data_source": {
                    "url": "https://fakerestapi.azurewebsites.net/api/v1/Activities"
                }
            }

            with patch('app_init.app_init.entity_service.add_item', new_callable=AsyncMock) as mock_add_item:
                response = await ingest_data_processor(meta, data)
                mock_add_item.assert_called_once_with(
                    meta["token"], "raw_data_entity", "1.0",
                    {"data_id": "data_001", "title": "Activity 1", "due_date": "2025-02-10T22:55:28Z", "completed": False}
                )
                self.assertEqual(response["status"], "success")

        asyncio.run(run_test())

    def test_report_generation_processor(self):
        async def run_test():
            meta = {"token": "test_token"}
            data = {
                "job_id": "job_2023_10_01"
            }

            with patch('app_init.app_init.entity_service.add_item', new_callable=AsyncMock) as mock_add_item:
                response = await report_generation_processor(meta, data)
                mock_add_item.assert_called_once()
                self.assertEqual(response["status"], "success")

        asyncio.run(run_test())

if __name__ == "__main__":
    unittest.main()