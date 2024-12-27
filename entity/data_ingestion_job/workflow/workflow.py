import logging
import unittest
from unittest.mock import patch
from common.app_init import entity_service, ai_service
from common.config.config import ENTITY_VERSION, TRINO_AI_API
from common.service.trino_service import get_trino_schema_id_by_entity_name
from common.util.utils import read_json_file, parse_json
from entity.raw_data_entity.connections.connections import ingest_data

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def ingest_raw_data(meta, data):
    logger.info("Starting process to ingest raw data.")
    try:
        request_params = data.get("request_parameters", {})
        response_data = ingest_data(
            code=request_params.get("code"),
            country=request_params.get("country"),
            name=request_params.get("name"),
        )
        raw_data_entity_id = entity_service.add_item(
            meta["token"], "raw_data_entity", ENTITY_VERSION, response_data
        )
        data.setdefault("raw_data_entity", {})["technical_id"] = raw_data_entity_id
        logger.info("Raw data entity saved successfully.")
    except Exception as e:
        logger.error(f"Error in ingest_raw_data: {e}")
        raise


def aggregate_raw_data(meta, data):
    logger.info("Starting process to aggregate raw data.")
    try:
        base_dir = os.path.abspath(os.path.join(__file__, "../../../"))
        aggregated_data_entity_path = os.path.join(
            base_dir, "aggregated_data_entity", "aggregated_data_entity.json"
        )
        aggregated_data_entity_schema = read_json_file(aggregated_data_entity_path)
        aggregated_data = ai_service.ai_chat(
            token=meta["token"],
            chat_id=get_trino_schema_id_by_entity_name("raw_data_entity"),
            ai_endpoint=TRINO_AI_API,
            ai_question=f"Could you please return json report based on this schema: {json.dumps(aggregated_data_entity_schema)}. Return only json",
        )
        aggregated_data_entity_data = json.loads(parse_json(aggregated_data))
        aggregated_data_entity_id = entity_service.add_item(
            meta["token"],
            "aggregated_data_entity",
            ENTITY_VERSION,
            aggregated_data_entity_data,
        )
        data.setdefault("aggregated_data_entity", {})[
            "technical_id"
        ] = aggregated_data_entity_id
        logger.info("Aggregated data entity saved successfully.")
    except Exception as e:
        logger.error(f"Error in aggregate_raw_data: {e}")
        raise


def send_email_process(meta, data):
    logger.info("Starting process to send email.")
    try:
        aggregated_data_entity = entity_service.get_item(
            meta["token"],
            "aggregated_data_entity",
            ENTITY_VERSION,
            data.get("aggregated_data_entity").get("technical_id"),
        )
        logger.info(f"Sending email with aggregated data: {aggregated_data_entity}")
        logger.info("Email sent successfully.")
    except Exception as e:
        logger.error(f"Error in send_email_process: {e}")
        raise


class TestDataIngestionJob(unittest.TestCase):

    @patch("entity.raw_data_entity.connections.connections.ingest_data")
    @patch("common.app_init.entity_service.add_item")
    def test_ingest_raw_data(self, mock_entity_service, mock_ingest_data):
        mock_ingest_data.return_value = [
            {
                "brpCode": "579000282425",
                "brpName": "42 Renaissance ApS",
                "country": "DK",
            }
        ]
        mock_entity_service.return_value = "raw_data_entity_id"
        meta = {"token": "test_token"}
        data = {
            "request_parameters": {"code": "579000282425", "country": "DK", "name": ""}
        }
        ingest_raw_data(meta, data)
        mock_entity_service.assert_called_once()

    @patch("common.app_init.entity_service.add_item")
    @patch("common.app_init.ai_service.ai_chat")
    @patch("common.service.trino_service.get_trino_schema_id_by_entity_name")
    def test_aggregate_raw_data(
        self, mock_get_trino_schema, mock_ai_chat, mock_entity_service
    ):
        mock_ai_chat.return_value = '{"aggregated_data": "dummy_aggregated_data"}'
        mock_entity_service.return_value = "aggregated_data_entity_id"
        mock_get_trino_schema.return_value = "response_data_entity_id"
        meta = {"token": "test_token"}
        data = {}
        aggregate_raw_data(meta, data)
        mock_entity_service.assert_called_once()

    @patch("common.app_init.entity_service.get_item")
    def test_send_email_process(self, mock_get_item):
        mock_get_item.return_value = {"aggregated_data": "dummy_data"}
        meta = {"token": "test_token"}
        data = {"aggregated_data_entity": {"technical_id": "aggregated_data_entity_id"}}
        send_email_process(meta, data)
        mock_get_item.assert_called_once()


if __name__ == "__main__":
    unittest.main()
