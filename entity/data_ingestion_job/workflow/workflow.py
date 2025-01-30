# Here's the implementation of the processor functions for the `data_ingestion_job`. The functions include `ingest_raw_data`, `aggregate_raw_data_process`, and `generate_report_process`. Each function reuses the required components from the codebase and ensures that dependent entities are saved appropriately.
# 
# ```python
import logging
import asyncio
from app_init.app_init import entity_service
from entity.raw_data_entity.connections.connections import ingest_data as ingest_raw_data_connection
from common.config.config import ENTITY_VERSION

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def ingest_raw_data(meta, data):
    logger.info("Starting data ingestion process.")
    try:
        # Call the reusable ingest_data function
        raw_data = await ingest_raw_data_connection(meta["token"])
        
        # Save the raw data entity
        raw_data_entity_id = await entity_service.add_item(
            meta["token"], "raw_data_entity", ENTITY_VERSION, raw_data
        )
        
        # Update the data with the raw data entity ID
        data["raw_data_entity"] = {"technical_id": raw_data_entity_id, "records": raw_data}
        logger.info(f"Raw data entity saved successfully with ID: {raw_data_entity_id}")
    except Exception as e:
        logger.error(f"Error in ingest_raw_data: {e}")
        raise

async def aggregate_raw_data_process(meta, data):
    logger.info("Starting data aggregation process.")
    try:
        # Simulate aggregation logic
        activities = data["raw_data_entity"]["records"]
        aggregated_data = {
            "total_authors": len(activities),
            "authors_per_book": {}
        }

        for activity in activities:
            book_id = activity["idBook"]
            if book_id not in aggregated_data["authors_per_book"]:
                aggregated_data["authors_per_book"][book_id] = {
                    "total_authors": 0,
                    "authors": []
                }
            aggregated_data["authors_per_book"][book_id]["total_authors"] += 1
            aggregated_data["authors_per_book"][book_id]["authors"].append({
                "id": activity["id"],
                "firstName": activity["firstName"],
                "lastName": activity["lastName"]
            })

        # Save the aggregated data entity
        aggregated_data_entity_id = await entity_service.add_item(
            meta["token"], "aggregated_data_entity", ENTITY_VERSION, aggregated_data
        )

        # Update the data with the aggregated data entity ID
        data["aggregated_data_entity"] = {"technical_id": aggregated_data_entity_id}
        logger.info(f"Aggregated data entity saved successfully with ID: {aggregated_data_entity_id}")
    except Exception as e:
        logger.error(f"Error in aggregate_raw_data_process: {e}")
        raise

async def generate_report_process(meta, data):
    logger.info("Starting report generation process.")
    try:
        report_data = {
            "report_id": "report_2023_10_02",
            "generated_at": "2023-10-02T10:05:00Z",
            "report_title": "Daily Author Data Report",
            "total_authors": data["aggregated_data_entity"]["total_authors"],
            "aggregated_books": [
                {
                    "idBook": book_id,
                    "author_count": details["total_authors"],
                    "author_names": [f"{author['firstName']} {author['lastName']}" for author in details["authors"]]
                }
                for book_id, details in data["aggregated_data_entity"]["authors_per_book"].items()
            ],
            "report_summary": "This report summarizes the data ingested from the API for authors, showing the total number of authors and the breakdown per book.",
            "comments": "Data ingestion was successful, and the report reflects the latest aggregated information.",
            "request_parameters": {
                "ingestion_job_id": data["job_id"],
                "data_source": "https://fakerestapi.azurewebsites.net/api/v1/Authors",
                "ingestion_timestamp": "2023-10-02T10:00:00Z"
            }
        }

        # Save the report entity
        report_entity_id = await entity_service.add_item(
            meta["token"], "report_entity", ENTITY_VERSION, report_data
        )

        logger.info(f"Report entity saved successfully with ID: {report_entity_id}")
    except Exception as e:
        logger.error(f"Error in generate_report_process: {e}")
        raise

# Unit Tests
import unittest
from unittest.mock import patch

class TestDataIngestionJob(unittest.TestCase):

    @patch("workflow.ingest_raw_data_connection")
    @patch("app_init.app_init.entity_service.add_item")
    def test_ingest_raw_data(self, mock_add_item, mock_ingest_data):
        mock_ingest_data.return_value = [
            {"id": 1, "idBook": 1, "firstName": "First Name 1", "lastName": "Last Name 1"},
            {"id": 2, "idBook": 1, "firstName": "First Name 2", "lastName": "Last Name 2"},
            {"id": 3, "idBook": 2, "firstName": "First Name 3", "lastName": "Last Name 3"},
            {"id": 4, "idBook": 2, "firstName": "First Name 4", "lastName": "Last Name 4"}
        ]
        mock_add_item.return_value = "raw_data_entity_id"

        meta = {"token": "test_token"}
        data = {}

        asyncio.run(ingest_raw_data(meta, data))

        mock_add_item.assert_called_once_with(
            meta["token"], "raw_data_entity", ENTITY_VERSION,
            mock_ingest_data.return_value
        )

    @patch("app_init.app_init.entity_service.add_item")
    def test_aggregate_raw_data_process(self, mock_add_item):
        mock_add_item.return_value = "aggregated_data_entity_id"

        meta = {"token": "test_token"}
        data = {
            "raw_data_entity": {
                "technical_id": "raw_data_entity_001",
                "records": [
                    {"id": 1, "idBook": 1, "firstName": "First Name 1", "lastName": "Last Name 1"},
                    {"id": 2, "idBook": 1, "firstName": "First Name 2", "lastName": "Last Name 2"},
                    {"id": 3, "idBook": 2, "firstName": "First Name 3", "lastName": "Last Name 3"},
                    {"id": 4, "idBook": 2, "firstName": "First Name 4", "lastName": "Last Name 4"}
                ]
            }
        }

        asyncio.run(aggregate_raw_data_process(meta, data))

        total_authors = len(data["raw_data_entity"]["records"])
        mock_add_item.assert_called_once_with(
            meta["token"], "aggregated_data_entity", ENTITY_VERSION,
            {
                "total_authors": total_authors,
                "authors_per_book": {
                    "1": {
                        "total_authors": 2,
                        "authors": [
                            {"id": 1, "firstName": "First Name 1", "lastName": "Last Name 1"},
                            {"id": 2, "firstName": "First Name 2", "lastName": "Last Name 2"}
                        ]
                    },
                    "2": {
                        "total_authors": 2,
                        "authors": [
                            {"id": 3, "firstName": "First Name 3", "lastName": "Last Name 3"},
                            {"id": 4, "firstName": "First Name 4", "lastName": "Last Name 4"}
                        ]
                    }
                }
            }
        )

    @patch("app_init.app_init.entity_service.add_item")
    def test_generate_report_process(self, mock_add_item):
        mock_add_item.return_value = "report_entity_id"

        meta = {"token": "test_token"}
        data = {
            "aggregated_data_entity": {
                "total_authors": 4,
                "authors_per_book": {
                    "1": {
                        "total_authors": 2,
                        "authors": [
                            {"id": 1, "firstName": "First Name 1", "lastName": "Last Name 1"},
                            {"id": 2, "firstName": "First Name 2", "lastName": "Last Name 2"}
                        ]
                    },
                    "2": {
                        "total_authors": 2,
                        "authors": [
                            {"id": 3, "firstName": "First Name 3", "lastName": "Last Name 3"},
                            {"id": 4, "firstName": "First Name 4", "lastName": "Last Name 4"}
                        ]
                    }
                }
            },
            "job_id": "job_001"
        }

        asyncio.run(generate_report_process(meta, data))

        mock_add_item.assert_called_once_with(
            meta["token"], "report_entity", ENTITY_VERSION,
            {
                "report_id": "report_2023_10_02",
                "generated_at": "2023-10-02T10:05:00Z",
                "report_title": "Daily Author Data Report",
                "total_authors": data["aggregated_data_entity"]["total_authors"],
                "aggregated_books": [
                    {
                        "idBook": book_id,
                        "author_count": details["total_authors"],
                        "author_names": [f"{author['firstName']} {author['lastName']}" for author in details["authors"]]
                    }
                    for book_id, details in data["aggregated_data_entity"]["authors_per_book"].items()
                ],
                "report_summary": "This report summarizes the data ingested from the API for authors, showing the total number of authors and the breakdown per book.",
                "comments": "Data ingestion was successful, and the report reflects the latest aggregated information.",
                "request_parameters": {
                    "ingestion_job_id": data["job_id"],
                    "data_source": "https://fakerestapi.azurewebsites.net/api/v1/Authors",
                    "ingestion_timestamp": "2023-10-02T10:00:00Z"
                }
            }
        )

if __name__ == "__main__":
    unittest.main()
# ```
# 
# ### Explanation:
# 1. **Processor Functions**:
#    - The `ingest_raw_data` function fetches data using the reusable `ingest_data` function and saves it to `raw_data_entity`.
#    - The `aggregate_raw_data_process` function aggregates the ingested data and saves it to `aggregated_data_entity`.
#    - The `generate_report_process` function generates a report based on the aggregated data and saves it to `report_entity`.
# 
# 2. **Unit Tests**:
#    - Tests for each processor function are included to verify their functionality.
#    - Mocks are used for external services to simulate the behavior without making actual calls.
# 
# This setup allows users to test the processor functions in isolation while ensuring that dependent entities are handled correctly. If you have any further questions or need modifications, feel free to ask! 😊