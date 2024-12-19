from common.service.service import EntityServiceImpl
from common.config.config import ENTITY_VERSION
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

service = EntityServiceImpl()

def schedule_data_ingestion_job():
    job_entity = {'can_proceed': True, 'entity': {'entity_name': 'data_ingestion_job', 'entity_type': 'JOB', 'entity_source': 'SCHEDULED', 'job_schedule': '0 * * * *', 'last_run': '2023-10-05T12:00:00Z', 'status': 'completed', 'ingestion_parameters': {'code': 'sample_code', 'country': 'FI', 'name': 'sample_name'}, 'data_ingested': {'total_records': 150, 'record_sample': [{'id': 1, 'name': 'Responsible Party A', 'code': 'RP001', 'country': 'FI'}, {'id': 2, 'name': 'Responsible Party B', 'code': 'RP002', 'country': 'FI'}], 'ingestion_time': '2023-10-05T12:01:00Z'}}}
    
    try:
        service.add_item('your_token', 'data_ingestion_job', ENTITY_VERSION, job_entity)
        logger.info('Job entity saved successfully.')
    except Exception as e:
        logger.error(f'Error saving job entity: {e}')  # Log any error

if __name__ == '__main__':
    schedule_data_ingestion_job()