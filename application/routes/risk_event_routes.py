from quart import Blueprint, request, jsonify
from services.services import get_entity_service
from application.entity.risk_event.version_1.risk_event import RiskEvent
from application.processor.risk_processors import RiskMonitoringProcessor
from typing import Dict, Tuple, Any

risk_event_routes = Blueprint('risk_event_routes', __name__, url_prefix='/api/risk_events')

@risk_event_routes.route('/', methods=['POST'])
async def create_risk_event() -> Tuple[Dict[str, Any], int]:
    """
    Creates a new risk event.
    """
    data = await request.get_json()
    entity_service = get_entity_service()
    risk_event = await entity_service.save(data, RiskEvent.ENTITY_NAME, RiskEvent.ENTITY_VERSION)
    return risk_event.data.model_dump(), 201

@risk_event_routes.route('/<entity_id>', methods=['GET'])
async def get_risk_event(entity_id: str) -> Tuple[Dict[str, Any], int]:
    """
    Retrieves a risk event by its ID.
    """
    entity_service = get_entity_service()
    risk_event = await entity_service.get_by_id(entity_id, RiskEvent.ENTITY_NAME, RiskEvent.ENTITY_VERSION)
    if risk_event:
        return risk_event.data.model_dump(), 200
    return {}, 404

@risk_event_routes.route('/check/<portfolio_id>', methods=['POST'])
async def check_risk(portfolio_id: str) -> Tuple[Dict[str, str], int]:
    """
    Triggers a risk check for a portfolio.
    """
    processor = RiskMonitoringProcessor()
    await processor.check_risk(portfolio_id)
    return {"status": "Risk check triggered"}, 200
