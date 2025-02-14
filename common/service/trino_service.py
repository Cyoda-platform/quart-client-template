from common.config.config import CYODA_AI_URL
from common.util.utils import send_post_request

async def get_trino_schema_id_by_entity_name(entity_name: str):
    return "2f303900-d8e3-11ef-a78b-ea51a4527ea1"

#runs sql to retrieve data
async def run_sql_query(token, query):
    resp = await send_post_request(token, CYODA_AI_URL, "api/v1/trino/run-query", query)
    return resp.get('json')["message"]