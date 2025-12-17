from quart import Blueprint, request, jsonify
from common.service.service import get_entity_service
from application.entity.risk_event.version_1.risk_event import RiskEvent
from application.processor.risk_processors import RiskMonitoringProcessor

risk_event_routes = Blueprint('risk_event_routes', __name__, url_prefix='/api/risk_events')

@risk_event_routes.route('/', methods=['POST'])
async def create_risk_event():
    """
    Creates a new risk event.
    """
    data = await request.get_json()
    entity_service = get_entity_service()
    risk_event = await entity_service.create(RiskEvent.ENTITY_NAME, RiskEvent.ENTITY_VERSION, data)
    return jsonify(risk_event.to_dict()), 201

@risk_event_routes.route('/<entity_id>', methods=['GET'])
async def get_risk_event(entity_id: str):
    """
    Retrieves a risk event by its ID.
    """
    entity_service = get_entity_service()
    risk_event = await entity_service.get(entity_id)
    return jsonify(risk_event.to_dict())

@risk_event_routes.route('/check/<portfolio_id>', methods=['POST'])
async def check_risk(portfolio_id: str):
    """
    Triggers a risk check for a portfolio.
    """
    processor = RiskMonitoringProcessor()
    await processor.check_risk(portfolio_id)
    return jsonify({"status": "Risk check triggered"}), 200
