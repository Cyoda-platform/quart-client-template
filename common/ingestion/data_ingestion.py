import logging
from pathlib import Path

from common.config.config import CYODA_API_URL, ENTITY_VERSION
from common.repository.cyoda.cyoda_repository import CyodaRepository
from common.util.utils import read_file, send_post_request, send_get_request

logger = logging.getLogger(__name__)

repository = CyodaRepository()
def ingest_data_from_connection(token, entity_name):
    file_path = Path(__file__).resolve().parent.parent.parent / f'entity/{entity_name}/ingestion/ingestion_request.json'
    data = read_file(file_path)
    resp = send_post_request(token, CYODA_API_URL, "data-source/request/request", data)
    return resp.json()

def get_data_ingestion_status(token, request_id):
    resp = send_get_request(token, CYODA_API_URL, f"data-source/request/result/{request_id}")
    return resp.json()

def get_all_entities(token, entity_name):
    response = repository.find_all({"token":token, "entity_model": entity_name,"entity_version": ENTITY_VERSION})
    return response