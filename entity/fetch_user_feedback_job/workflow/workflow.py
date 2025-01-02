import logging

from common.app_init import entity_service, ai_service
from common.config.config import ENTITY_VERSION, TRINO_AI_API
from common.service.trino_service import get_trino_schema_id_by_entity_name
from common.util.utils import read_json_file, parse_json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def process_name(meta, data):
    try:
        entity = entity_service.get_item(
            meta["token"], "fetch_user_feedback_job", ENTITY_VERSION, data["id"]
        )
        # Logic to process the entity
        dependant_entity_data = data.get("dependant_entity_data")
        if dependant_entity_data:
            entity_service.add_item(
                meta["token"],
                "dependant_entity_name",
                ENTITY_VERSION,
                dependant_entity_data,
            )
    except Exception as e:
        logger.error(f"Failed to process entity: {e}")
        return {"can_proceed": False, "error": str(e)}


def data_aggregation_process_name(meta, data):
    base_dir = os.path.abspath(os.path.join(__file__, "../../../"))
    aggregated_data_entity_path = os.path.join(
        base_dir, "aggregated_data_entity", "aggregated_data_entity.json"
    )
    aggregated_data_entity_schema = read_json_file(aggregated_data_entity_path)
    try:
        aggregated_data = ai_service.ai_chat(
            token=meta["token"],
            chat_id=get_trino_schema_id_by_entity_name("response_data_entity"),
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
    except Exception as e:
        logger.error(f"Error during data aggregation: {e}")
        return {"can_proceed": False, "error": str(e)}


class TestSendEmailProcess(unittest.TestCase):
    @patch("common.app_init.entity_service.add_item")
    def test_send_email_process(self, mock_entity_service):
        mock_entity_service.return_value = "12345"
        response = process_name(
            {"token": "dummy_token"}, {"id": "test_id", "dependant_entity_data": {}}
        )
        self.assertIn("can_proceed", response)
        self.assertFalse(response["can_proceed"])


if __name__ == "__main__":
    unittest.main()
