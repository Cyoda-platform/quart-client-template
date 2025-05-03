from datetime import timezone, datetime
import logging
from quart import Blueprint, request, abort
from quart_schema import validate, validate_querystring, tag, operation_id
from app_init.app_init import BeanFactory
from common.service.entity_service_interface import EntityService

logger = logging.getLogger(__name__)
FINAL_STATES = {"FAILURE", "SUCCESS", "CANCELLED", "CANCELLED_BY_USER", "UNKNOWN", "FINISHED"}
PROCESSING_STATE = "PROCESSING"
routes_bp = Blueprint("routes", __name__)

factory = BeanFactory(config={"CHAT_REPOSITORY": "cyoda"})
entity_service: EntityService = factory.get_services()["entity_service"]


