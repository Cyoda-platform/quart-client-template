import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime

import httpx
from quart import Quart, jsonify, request, abort
from quart_schema import QuartSchema, validate_request, validate_querystring

from app_init.app_init import entity_service, cyoda_token
from common.config.config import ENTITY_VERSION
from common.repository.cyoda.cyoda_init import init_cyoda

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Initialize Quart app and QuartSchema
app = Quart(__name__)
QuartSchema(app)

# Global in-memory job statuses (Mock persistence for background jobs)
ENTITY_JOBS = {}  # Stores job statuses by job id

# Data classes for request validations
@dataclass
class FetchParams:
    # Supports an optional 'limit'
    limit: int = 0  # 0 means no limit

@dataclass
class UserQuery:
    # Query parameters for GET /api/users endpoint
    name: str = ""
    email: str = ""

# Simple job id generation helper
def generate_job_id():
    return f"job-{int(datetime.utcnow().timestamp())}"

# Workflow function for processing a single user entity.
# This function is invoked asynchronously before the entity is persisted.
# It takes the entity as the only argument. Modify the entity state directly.
async def process_users(entity):
    # Example: add a processing timestamp
    entity["processed_at"] = datetime.utcnow().isoformat()
    # Simulate additional asynchronous tasks such as contacting a supplementary API
    # For demonstration, we'll simulate a brief delay.
    await asyncio.sleep(0.1)
    # You can add more async logic here.
    return entity

# Background function to process multiple user entities.
# This function uses the workflow function (process_users) for each entity.
async def process_users_job(job_id: str, data: list):
    try:
        logger.info("Start processing user data for job_id: %s", job_id)
        # Process each user concurrently using the workflow function via entity_service.add_item.
        tasks = []
        for user in data:
            # entity_service.add_item applies process_users to the entity asynchronously
            tasks.append(
                entity_service.add_item(
                    token=cyoda_token,
                    entity_model="users",
                    entity_version=ENTITY_VERSION,
                    entity=user,
                    workflow=process_users
                )
            )
        # Wait for all the add_item tasks to complete.
        await asyncio.gather(*tasks)
        ENTITY_JOBS[job_id]["status"] = "completed"
        logger.info("Completed processing user data for job_id: %s", job_id)
    except Exception as e:
        ENTITY_JOBS[job_id]["status"] = "failed"
        logger.exception(e)

# Endpoint to fetch user data from an external API and initiate asynchronous processing.
@app.route("/api/users/fetch", methods=["POST"])
@validate_request(FetchParams)
async def fetch_users(data: FetchParams):
    try:
        # Fetch external user data.
        async with httpx.AsyncClient() as client:
            response = await client.get("https://jsonplaceholder.typicode.com/users")
            response.raise_for_status()
            external_data = response.json()
        
        # Optionally limit the fetched data.
        if data.limit > 0:
            external_data = external_data[:data.limit]
        
        # Generate a job id and store initial job status.
        job_id = generate_job_id()
        ENTITY_JOBS[job_id] = {"status": "processing", "requestedAt": datetime.utcnow().isoformat()}
        
        # Launch background processing: each user will be processed with process_users workflow.
        asyncio.create_task(process_users_job(job_id, external_data))
        
        # Return a response indicating that data fetch and processing have been initiated.
        return jsonify({
            "message": "User data fetch initiated.",
            "count": len(external_data),
            "jobId": job_id
        })
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to fetch user data."}), 500

# Endpoint to retrieve filtered users.
@validate_querystring(UserQuery)
@app.route("/api/users", methods=["GET"])
async def get_users():
    try:
        # Retrieve query parameters.
        name_filter = request.args.get("name", "").lower()
        email_filter = request.args.get("email", "").lower()
        
        # Get all users from the external entity service.
        users = await entity_service.get_items(
            token=cyoda_token,
            entity_model="users",
            entity_version=ENTITY_VERSION,
        )
        # Apply filters and include only basic info.
        filtered_users = []
        for user in users:
            if name_filter and name_filter not in user.get("name", "").lower():
                continue
            if email_filter and email_filter not in user.get("email", "").lower():
                continue
            filtered_users.append({
                "id": user.get("id"),
                "name": user.get("name"),
                "email": user.get("email"),
                "phone": user.get("phone"),
                "website": user.get("website")
            })
        
        return jsonify(filtered_users)
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to retrieve user list."}), 500

# Endpoint to retrieve detailed information for a single user.
@app.route("/api/users/<int:user_id>", methods=["GET"])
async def get_user_detail(user_id: int):
    try:
        user = await entity_service.get_item(
            token=cyoda_token,
            entity_model="users",
            entity_version=ENTITY_VERSION,
            technical_id=user_id
        )
        if user is None:
            abort(404, description="User not found.")
        return jsonify(user)
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to retrieve user detail."}), 500

# Startup initialization before serving requests.
@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)