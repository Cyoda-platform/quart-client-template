from quart import Blueprint, request, jsonify
from app_init.app_init import entity_service, cyoda_token
from common.config.config import ENTITY_VERSION
import uuid
import asyncio

api_bp_company = Blueprint('api/company', __name__)

ENTITY_MODEL = 'company'

@api_bp_company.route('/companies', methods=['POST'])
async def add_company():
    """Create a new company."""
    data = await request.json
    if not data:
        return jsonify({"error": "No data provided"}), 400
    try:
        company_id = await entity_service.add_item(
            token=cyoda_token,
            entity_model=ENTITY_MODEL,
            entity_version=ENTITY_VERSION,
            entity=data
        )
        return jsonify({'company_id': company_id}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@api_bp_company.route('/company/<id>', methods=['GET'])
async def get_id(id):
    """Retrieve a company by ID."""
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

@api_bp_company.route('/companies', methods=['GET'])
async def get_companys():
    """Retrieve all companies entries."""
    try:
        data = await entity_service.get_items(
            token=cyoda_token,
            entity_model=ENTITY_MODEL,
            entity_version=ENTITY_VERSION
        )
        return jsonify({"data": data}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
