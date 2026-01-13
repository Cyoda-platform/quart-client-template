# errors.py
import logging
from typing import Any, Tuple

from quart import Quart, jsonify
from werkzeug.exceptions import NotFound

from common.exception.exceptions import ChatNotFoundError, UnauthorizedAccessError

logger = logging.getLogger(__name__)


def register_error_handlers(app: Quart) -> None:
    @app.errorhandler(UnauthorizedAccessError)
    async def handle_unauthorized_exception(
        error: UnauthorizedAccessError,
    ) -> Tuple[Any, int]:
        return jsonify({"error": str(error)}), 401

    @app.errorhandler(ChatNotFoundError)
    async def handle_chat_not_found_exception(
        error: ChatNotFoundError,
    ) -> Tuple[Any, int]:
        return jsonify({"error": str(error)}), 404

    @app.errorhandler(NotFound)
    async def handle_not_found_exception(error: NotFound) -> Tuple[Any, int]:
        logger.debug("404 Not Found: %s", error.description)
        return jsonify({"error": "Not found", "code": "NOT_FOUND"}), 404

    @app.errorhandler(Exception)
    async def handle_any_exception(error: Exception) -> Tuple[Any, int]:
        logger.exception(error)
        return jsonify({"error": str(error)}), 500
