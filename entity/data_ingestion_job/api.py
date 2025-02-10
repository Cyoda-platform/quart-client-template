# ```python
import logging
from quart import Blueprint, request, jsonify
from app_init.app_init import entity_service
from common.config.config import ENTITY_VERSION, cyoda_token

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

api_bp_data_ingestion_job = Blueprint('api_data_ingestion_job', __name__)

@api_bp_data_ingestion_job.route('/add', methods=['POST'])
async def add_data_ingestion_job():
    """API endpoint to add a data ingestion job."""
    try:
        job_data = await request.get_json()
        job_data["token"] = cyoda_token
        job_id = await entity_service.add_item(
            job_data["token"],
            "data_ingestion_job",
            ENTITY_VERSION,
            {
                "job_id": job_data["job_id"],
                "name": job_data["name"],
                "description": "Job responsible for ingesting category data.",
                "scheduled_time": job_data["scheduled_time"],
                "status": "pending",
                "request_parameters": {
                    "api_url": "https://api.practicesoftwaretesting.com/categories/tree",
                    "headers": {"accept": "application/json"}
                }
            }
        )
        return jsonify({"technical_id": job_id}), 201
    except Exception as e:
        logger.error(f"Error adding data ingestion job: {e}")
        return jsonify({"error": "Failed to add data ingestion job."}), 500
# ```
# 
# ### Explanation of the Code:
# - This API blueprint handles the addition of the **`data_ingestion_job`** entity.
# - The endpoint **`/add`** receives a POST request containing the job data, including the job ID, name, and scheduled time.
# - It utilizes the **`entity_service`** to save the job, passing the necessary parameters, including the entity version defined by **`ENTITY_VERSION`**.
# - Upon successful addition, it returns the technical ID of the newly created job; otherwise, it returns an error message.
# 
# If you have any further questions or need modifications, please let me know! I'm here to assist you!