from quart import Blueprint, request, jsonify
from app_init.app_init import entity_service, cyoda_token
from common.config.config import ENTITY_VERSION
import uuid
import asyncio

api_bp_job = Blueprint('api/job', __name__)

ENTITY_MODEL = 'job'

@api_bp_job.route('/jobs', methods=['POST'])
async def add_job():
    """Create a new job."""
    data = await request.json
    if not data:
        return jsonify({"error": "No data provided"}), 400
    try:
        job_id = await entity_service.add_item(
            token=cyoda_token,
            entity_model=ENTITY_MODEL,
            entity_version=ENTITY_VERSION,
            entity=data
        )
        return jsonify({'job_id': job_id}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@api_bp_job.route('/job/<id>', methods=['GET'])
async def get_id(id):
    """Retrieve a job by ID."""
    try:
        data = await entity_service.get_item(
            token=cyoda_token,
            entity_model=ENTITY_MODEL,
            entity_version=ENTITY_VERSION,
            technical_id=id
        )
        return jsonify({"data": data}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@api_bp_job.route('/jobs', methods=['GET'])
async def get_jobs():
    """Retrieve all jobs entries."""
    try:
        data = await entity_service.get_items(
            token=cyoda_token,
            entity_model=ENTITY_MODEL,
            entity_version=ENTITY_VERSION
        )
        return jsonify({"data": data}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
