# errors.py
import logging
from quart import jsonify

from common.exception.exceptions import UnauthorizedAccessException, ChatNotFoundException

logger = logging.getLogger(__name__)

def register_error_handlers(app):
    @app.errorhandler(UnauthorizedAccessException)
    async def handle_unauthorized_exception(error):
        return jsonify({"error": str(error)}), 401

    @app.errorhandler(ChatNotFoundException)
    async def handle_chat_not_found_exception(error):
        return jsonify({"error": str(error)}), 404

    @app.errorhandler(Exception)
    async def handle_any_exception(error):
        logger.exception(error)
        return jsonify({"error": str(error)}), 500
