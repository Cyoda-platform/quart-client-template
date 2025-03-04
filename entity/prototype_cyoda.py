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
ENTITY_JOBS = {}  # Dictionary to store job statuses

# Data classes for request validations
@dataclass
class FetchParams:
    # TODO: Add additional fields if needed; currently only supports an optional 'limit'
    limit: int = 0  # 0 means no limit

@dataclass
class UserQuery:
    # Query parameters for GET /api/users endpoint
    name: str = ""
    email: str = ""

# TODO: In a complete implementation, replace the simple job id generation with a proper UUID generator.
def generate_job_id():
    return f"job-{int(datetime.utcnow().timestamp())}"

async def process_users(job_id: str, data: list):
    """Process and store user data in background."""
    try:
        logger.info("Start processing user data for job_id: %s", job_id)
        # For each user in the provided data, add the user via the external entity service.
        for user in data:
            await entity_service.add_item(
                token=cyoda_token,
                entity_model="users",
                entity_version=ENTITY_VERSION,
                entity=user
            )
        ENTITY_JOBS[job_id]["status"] = "completed"
        logger.info("Completed processing user data for job_id: %s", job_id)
    except Exception as e:
        ENTITY_JOBS[job_id]["status"] = "failed"
        logger.exception(e)

# For POST endpoints, the route decorator is first, followed by the validation decorator.
@app.route("/api/users/fetch", methods=["POST"])
@validate_request(FetchParams)  # Workaround: for POST, place validate_request decorator after route decorator.
async def fetch_users(data: FetchParams):
    """Fetch user data from the external API and process it in a background task."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get("https://jsonplaceholder.typicode.com/users")
            response.raise_for_status()
            external_data = response.json()
        
        # Optionally use data.limit from FetchParams to restrict the amount of fetched data.
        if data.limit > 0:
            external_data = external_data[:data.limit]

        # Generate job id and add job status to our entity jobs store
        job_id = generate_job_id()
        ENTITY_JOBS[job_id] = {"status": "processing", "requestedAt": datetime.utcnow().isoformat()}

        # Fire and forget the processing task.
        asyncio.create_task(process_users(job_id, external_data))

        # Return a response indicating that data fetch has been initiated.
        return jsonify({
            "message": "User data fetch initiated.",
            "count": len(external_data),
            "jobId": job_id
        })
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to fetch user data."}), 500

# For GET endpoints with query parameters, the validation decorator is first.
@validate_querystring(UserQuery)  # Workaround: for GET, place validate_querystring decorator before route decorator.
@app.route("/api/users", methods=["GET"])
async def get_users():
    """Retrieve a list of users with basic contact details, and support filtering by name or email."""
    try:
        # Get query parameters using the standard approach.
        name_filter = request.args.get("name", "").lower()
        email_filter = request.args.get("email", "").lower()

        # Get all users from external entity service.
        users = await entity_service.get_items(
            token=cyoda_token,
            entity_model="users",
            entity_version=ENTITY_VERSION,
        )
        filtered_users = []
        for user in users:
            if name_filter and name_filter not in user.get("name", "").lower():
                continue
            if email_filter and email_filter not in user.get("email", "").lower():
                continue
            # Include only basic info.
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

# No validation needed for GET endpoints without request parameters.
@app.route("/api/users/<int:user_id>", methods=["GET"])
async def get_user_detail(user_id: int):
    """Retrieve detailed information for a single user, including address and company details."""
    try:
        # Retrieve the user from the external entity service.
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

@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)