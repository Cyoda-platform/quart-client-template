from common.config.config import CYODA_AI_URL
from common.repository.cyoda.cyoda_init import load_config_json
from common.util.utils import send_post_request

def get_trino_schema_id_by_entity_name(entity_name: str):
    config = load_config_json()
    return config.get(entity_name)

#runs sql to retrieve data
def run_sql_query(token, query):
    resp = send_post_request(token, CYODA_AI_URL, "api/v1/trino/run-query", query)
    return resp.json()["message"]