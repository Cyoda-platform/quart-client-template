import asyncio
import logging
from datetime import datetime
from typing import Dict
from dataclasses import dataclass

import httpx
from quart import Blueprint, jsonify, request
from quart_schema import validate_request

from app_init.app_init import BeanFactory
from common.config.config import ENTITY_VERSION

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

routes_bp = Blueprint('routes', __name__)

factory = BeanFactory(config={'CHAT_REPOSITORY': 'cyoda'})
entity_service = factory.get_services()['entity_service']
cyoda_auth_service = factory.get_services()["cyoda_auth_service"]

@dataclass
class HelloRequest:
    trigger: str

# In-memory local cache to track job status only (no entity data storage)
entity_job: Dict[str, Dict] = {}
cache_lock = asyncio.Lock()

async def process_entity(job_id: str, data: dict):
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get("https://httpbin.org/delay/1")
            resp.raise_for_status()
            message = "Hello World!"
            async with cache_lock:
                entity_job[job_id]["status"] = "completed"
                entity_job[job_id]["message"] = message
                entity_job[job_id]["completedAt"] = datetime.utcnow().isoformat()
            logger.info(f"Job {job_id} completed successfully.")
    except Exception as e:
        async with cache_lock:
            entity_job[job_id]["status"] = "failed"
            entity_job[job_id]["error"] = str(e)
            entity_job[job_id]["completedAt"] = datetime.utcnow().isoformat()
        logger.exception(e)

@routes_bp.route("/hello", methods=["POST"])
@validate_request(HelloRequest)
async def trigger_hello(data: HelloRequest):
    if data.trigger != "hello_world":
        return jsonify({"status": "error", "message": "Invalid trigger value"}), 400

    job_id = datetime.utcnow().isoformat()
    async with cache_lock:
        entity_job[job_id] = {
            "status": "processing",
            "requestedAt": job_id,
        }

    asyncio.create_task(process_entity(job_id, data.__dict__))
    return jsonify({"status": "success", "job_id": job_id, "message": "Workflow started"}), 202

@routes_bp.route("/hello", methods=["GET"])
async def get_hello():
    async with cache_lock:
        completed_jobs = [job for job in entity_job.values() if job.get("status") == "completed"]
        if not completed_jobs:
            return jsonify({"message": "No completed Hello World message available."}), 404
        last_job = max(completed_jobs, key=lambda j: j["completedAt"])
        return jsonify({"message": last_job.get("message", "")})

# Workflow function for 'prototype' entity
async def process_prototype(entity: dict) -> dict:
    entity['processedAt'] = datetime.utcnow().isoformat()

    try:
        async with httpx.AsyncClient(timeout=5) as client:
            response = await client.get("https://httpbin.org/get")
            response.raise_for_status()
            result = response.json()
            entity['enrichment'] = result.get('url', 'unknown')
    except Exception as e:
        logger.warning(f"Failed to enrich prototype entity: {e}")

    await asyncio.sleep(0.1)
    return entity

@routes_bp.route("/prototype", methods=["POST"])
async def create_prototype():
    data = await request.get_json()
    if not isinstance(data, dict):
        return jsonify({"error": "Invalid JSON body"}), 400
    try:
        id = await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model="prototype",
            entity_version=ENTITY_VERSION,
            entity=data
        )
        return jsonify({"id": str(id)}), 202
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to create prototype"}), 500

@routes_bp.route("/prototype/<string:technical_id>", methods=["GET"])
async def get_prototype(technical_id: str):
    if not technical_id:
        return jsonify({"error": "Technical ID required"}), 400
    try:
        item = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model="prototype",
            entity_version=ENTITY_VERSION,
            technical_id=technical_id
        )
        if item is None:
            return jsonify({"error": "Prototype not found"}), 404
        return jsonify(item)
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to retrieve prototype"}), 500

@routes_bp.route("/prototype", methods=["GET"])
async def list_prototypes():
    try:
        items = await entity_service.get_items(
            token=cyoda_auth_service,
            entity_model="prototype",
            entity_version=ENTITY_VERSION,
        )
        return jsonify(items)
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to list prototypes"}), 500

@routes_bp.route("/prototype/<string:technical_id>", methods=["PUT"])
async def update_prototype(technical_id: str):
    if not technical_id:
        return jsonify({"error": "Technical ID required"}), 400
    data = await request.get_json()
    if not isinstance(data, dict):
        return jsonify({"error": "Invalid JSON body"}), 400
    try:
        await entity_service.update_item(
            token=cyoda_auth_service,
            entity_model="prototype",
            entity_version=ENTITY_VERSION,
            entity=data,
            technical_id=technical_id,
            meta={}
        )
        return jsonify({"status": "updated"})
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to update prototype"}), 500

@routes_bp.route("/prototype/<string:technical_id>", methods=["DELETE"])
async def delete_prototype(technical_id: str):
    if not technical_id:
        return jsonify({"error": "Technical ID required"}), 400
    try:
        await entity_service.delete_item(
            token=cyoda_auth_service,
            entity_model="prototype",
            entity_version=ENTITY_VERSION,
            technical_id=technical_id,
            meta={}
        )
        return jsonify({"status": "deleted"})
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to delete prototype"}), 500