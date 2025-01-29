# Sure! Below is the implementation of the processor functions for `london_houses_workflow`. The functions include `ingest_raw_data`, `analyze_data_process`, and `generate_report_process`. Each function will use existing functions where applicable and ensure that dependent entities are saved correctly.
# 
# ### Python Code Implementation
# ```python
import logging
import asyncio
from app_init.app_init import entity_service
from common.service.connections import ingest_data as ingest_raw_data_connection  # Importing existing ingestion function
from common.config.config import ENTITY_VERSION

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def ingest_raw_data(meta, data):
    logger.info("Starting data ingestion process for London houses.")
    try:
        # Call the reusable ingest_data function
        raw_data = await ingest_raw_data_connection(meta["token"])  # Pass token to ingest data

        # Save the raw data entity
        raw_data_entity_id = await entity_service.add_item(
            meta["token"], "london_houses_data", ENTITY_VERSION, raw_data
        )

        # Update the data with the raw data entity ID
        data["london_houses_data"] = {"technical_id": raw_data_entity_id, "records": raw_data}
        logger.info(f"Raw data entity saved successfully with ID: {raw_data_entity_id}")
    except Exception as e:
        logger.error(f"Error in ingest_raw_data: {e}")
        raise

async def analyze_data_process(meta, data):
    logger.info("Starting analysis process for London houses data.")
    try:
        # Retrieve the raw data
        raw_data = data["london_houses_data"]["records"]

        # Perform analysis on the data (mocked analysis logic)
        # Assume we're just calculating average price here
        prices = [house["price"] for house in raw_data]
        average_price = sum(prices) / len(prices) if prices else 0
        total_houses = len(raw_data)

        # Prepare the analysis entity data
        analysis_data = {
            "analysis_id": "analysis_2023_10_01",
            "summary": "Analysis of London houses.",
            "average_price": average_price,
            "total_houses": total_houses,
            "price_distribution": {},  # Add logic to populate this
        }

        # Save the analysis entity
        analysis_entity_id = await entity_service.add_item(
            meta["token"], "london_houses_analysis", ENTITY_VERSION, analysis_data
        )

        # Update the data with the analysis entity ID
        data["london_houses_analysis"] = {"technical_id": analysis_entity_id}
        logger.info(f"Analysis entity saved successfully with ID: {analysis_entity_id}")

    except Exception as e:
        logger.error(f"Error in analyze_data_process: {e}")
        raise

async def generate_report_process(meta, data):
    logger.info("Generating report based on the analysis results.")
    try:
        analysis_data = data["london_houses_analysis"]

        # Prepare the report entity data
        report_data = {
            "report_id": "report_2023_10_01",
            "report_title": "London Houses Market Analysis - October 2023",
            "generated_at": "2023-10-01T10:05:00Z",
            "total_houses_analyzed": data["london_houses_analysis"]["total_houses"],
            "average_price": data["london_houses_analysis"]["average_price"],
            "summary": "This report provides an overview of the London housing market.",
        }

        # Save the report entity
        report_entity_id = await entity_service.add_item(
            meta["token"], "london_houses_report", ENTITY_VERSION, report_data
        )

        # Update the data with the report entity ID
        data["london_houses_report"] = {"technical_id": report_entity_id}
        logger.info(f"Report entity saved successfully with ID: {report_entity_id}")

    except Exception as e:
        logger.error(f"Error in generate_report_process: {e}")
        raise

# Unit Tests
import unittest
from unittest.mock import patch

class TestLondonHousesWorkflow(unittest.TestCase):

    @patch("app_init.app_init.entity_service.add_item")
    @patch("common.service.connections.ingest_data")
    def test_ingest_raw_data(self, mock_ingest_data, mock_add_item):
        mock_ingest_data.return_value = [{"id": "1", "title": "Luxury Apartment", "location": "Central London", "price": 1200000.00}]
        mock_add_item.return_value = "raw_data_entity_id"

        meta = {"token": "test_token"}
        data = {}

        asyncio.run(ingest_raw_data(meta, data))

        mock_add_item.assert_called_once_with(meta["token"], "london_houses_data", ENTITY_VERSION, mock_ingest_data.return_value)

    @patch("app_init.app_init.entity_service.add_item")
    def test_analyze_data_process(self, mock_add_item):
        mock_add_item.return_value = "analysis_entity_id"

        meta = {"token": "test_token"}
        raw_data = [{"price": 1200000.00}, {"price": 950000.00}, {"price": 800000.00}]
        data = {"london_houses_data": {"records": raw_data}}

        asyncio.run(analyze_data_process(meta, data))

        self.assertEqual(data["london_houses_analysis"]["technical_id"], "analysis_entity_id")

    @patch("app_init.app_init.entity_service.add_item")
    def test_generate_report_process(self, mock_add_item):
        mock_add_item.return_value = "report_entity_id"

        meta = {"token": "test_token"}
        data = {
            "london_houses_analysis": {
                "total_houses": 3,
                "average_price": 1000000.00
            }
        }

        asyncio.run(generate_report_process(meta, data))

        self.assertEqual(data["london_houses_report"]["technical_id"], "report_entity_id")

if __name__ == "__main__":
    unittest.main()
# ```
# 
# ### Explanation
# 1. **Ingest Raw Data**: The `ingest_raw_data` function fetches data using the existing `ingest_data` function and saves it to the `london_houses_data` entity.
# 2. **Analyze Data**: The `analyze_data_process` function processes the downloaded raw data and saves the analysis results to the `london_houses_analysis` entity.
# 3. **Generate Report**: The `generate_report_process` function prepares a report based on the analysis results and saves it to the `london_houses_report` entity.
# 4. **Unit Tests**: Each processor function includes tests that mock the external service calls to validate the logic without requiring actual data.
# 
# Let me know if you need further adjustments or additional details! 😊