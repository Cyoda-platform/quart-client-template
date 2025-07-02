import asyncio
import logging
from datetime import datetime
from common.config.config import ENTITY_VERSION
from app_init.app_init import BeanFactory

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

factory = BeanFactory(config={'CHAT_REPOSITORY': 'cyoda'})
entity_service = factory.get_services()['entity_service']
cyoda_auth_service = factory.get_services()["cyoda_auth_service"]

async def condition_csv_url_present(entity: dict) -> bool:
    return bool(entity.get('csv_url'))

async def condition_csv_url_missing(entity: dict) -> bool:
    return not bool(entity.get('csv_url'))

async def download_data(entity: dict):
    job_id = entity.get('job_id', 'unknown')
    csv_url = entity.get('csv_url')
    try:
        logger.info(f"Job {job_id}: Starting data download from {csv_url}")
        df = await download_csv(csv_url)
        entity['dataframe'] = df
    except Exception as e:
        logger.exception(e)
        entity['download_error'] = str(e)

async def condition_data_downloaded(entity: dict) -> bool:
    return 'dataframe' in entity

async def analyze(entity: dict):
    job_id = entity.get('job_id', 'unknown')
    analysis_type = entity.get('analysis_type', 'summary')
    df = entity.get('dataframe')
    if df is None:
        raise ValueError("No data to analyze")
    logger.info(f"Job {job_id}: Data downloaded, starting analysis")
    analysis_result = analyze_data(df, analysis_type)
    entity['analysis_result'] = analysis_result

async def condition_analysis_done(entity: dict) -> bool:
    return 'analysis_result' in entity

async def send_report(entity: dict):
    job_id = entity.get('job_id', 'unknown')
    subscribers = entity.get('subscribers', [])
    analysis_result = entity.get('analysis_result')
    if analysis_result is None:
        raise ValueError("No analysis result to send")
    logger.info(f"Job {job_id}: Analysis complete, sending emails")
    await send_email_report(subscribers, analysis_result)

async def mark_failed(entity: dict):
    job_id = entity.get('job_id', 'unknown')
    error = entity.get('error', 'Unknown error')
    logger.error(f"Job {job_id}: Marking as failed with error: {error}")
    entity["status"] = "failed"
    if 'error' not in entity:
        entity["error"] = error
    entity["last_processed_at"] = datetime.utcnow().isoformat() + "Z"

async def mark_completed(entity: dict):
    job_id = entity.get('job_id', 'unknown')
    entity["status"] = "completed"
    entity["result"] = entity.get("analysis_result")
    entity["last_processed_at"] = datetime.utcnow().isoformat() + "Z"
    logger.info(f"Job {job_id}: Completed successfully")


# You need to define or import these functions in your module:
# async def download_csv(url: str) -> pd.DataFrame
# def analyze_data(df: pd.DataFrame, analysis_type: str) -> dict
# async def send_email_report(subscribers: list[str], report: dict) -> None