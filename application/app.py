import asyncio
import logging
from typing import Callable, Dict, Optional

from quart import Quart, Response
from quart_schema import QuartSchema, ResponseSchemaValidationError, hide

from application.routes.accounts import accounts_bp
from application.routes.instruments import instruments_bp

# Import blueprints for different route groups
from application.routes.orders import orders_bp
from application.routes.positions import positions_bp
from application.routes.risk_limits import risk_limits_bp
from application.routes.trades import trades_bp
from common.exception.exception_handler import (
    register_error_handlers as _register_error_handlers,
)
from services.services import get_grpc_client, initialize_services

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)

QuartSchema(
    app,
    info={"title": "Cyoda Client Application", "version": "1.0.0"},
    tags=[
        {
            "name": "ExampleEntities",
            "description": "ExampleEntity management endpoints",
        },
        {"name": "OtherEntities", "description": "OtherEntity management endpoints"},
        {"name": "System", "description": "System and health endpoints"},
    ],
    security=[{"bearerAuth": []}],
    security_schemes={
        "bearerAuth": {
            "type": "http",
            "scheme": "bearer",
        }
    },
)

# Register blueprints
app.register_blueprint(orders_bp)
app.register_blueprint(trades_bp)
app.register_blueprint(accounts_bp)
app.register_blueprint(instruments_bp)
app.register_blueprint(positions_bp)
app.register_blueprint(risk_limits_bp)

# Global holder for the background task to satisfy mypy
# (avoid setting arbitrary attrs on app)
_background_task: Optional[asyncio.Task[None]] = None


# Register error handlers for custom and generic exceptions
@app.errorhandler(ResponseSchemaValidationError)
async def handle_response_validation_error(
    error: ResponseSchemaValidationError,
) -> tuple[Dict[str, str], int]:
    # You can log/inspect `error` if needed
    return {"error": "VALIDATION"}, 500


# Give mypy a typed view of the external function (if it lacks type hints)
_register_error_handlers_typed: Callable[[Quart], None] = (  # type: ignore[assignment]
    _register_error_handlers
)
_register_error_handlers_typed(app)


@app.route("/favicon.ico")
@hide
def favicon() -> tuple[str, int]:
    return "", 200


# Startup tasks: initialize services and start the GRPC stream in the background
@app.before_serving
async def startup() -> None:
    from services.config import get_service_config, validate_configuration

    # Validate configuration and log any issues
    validation = validate_configuration()
    if not validation["valid"]:
        logger.error("Service configuration validation failed!")
        raise RuntimeError("Invalid service configuration")

    # Initialize services with validated configuration
    config = get_service_config()
    logger.info("Initializing services at application startup...")
    initialize_services(config)
    logger.info("All services initialized successfully at startup")

    # Get the gRPC client and start the stream
    grpc_client = get_grpc_client()

    # The stream method is expected to be an async coroutine returning None
    stream_coro = grpc_client.grpc_stream()
    global _background_task
    _background_task = asyncio.create_task(stream_coro)  # type: ignore[arg-type]


# Shutdown tasks: cancel the background tasks when shutting down
@app.after_serving
async def shutdown() -> None:
    """Cleanup tasks on shutdown."""
    logger.info("Shutting down application...")

    global _background_task
    # Cancel the background gRPC stream task
    if _background_task is not None:
        _background_task.cancel()
        try:
            await _background_task
        except asyncio.CancelledError:
            pass
        finally:
            _background_task = None

    logger.info("Application shutdown complete")


# Middleware to add CORS headers to every response
@app.before_serving
async def add_cors_headers() -> None:
    @app.after_request
    async def apply_cors(response: Response) -> Response:
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "*"
        response.headers["Access-Control-Allow-Credentials"] = "true"
        return response


if __name__ == "__main__":
    import os

    host = os.getenv("APP_HOST", "127.0.0.1")  # Default to localhost for security
    port = int(os.getenv("APP_PORT", "8000"))
    debug = os.getenv("APP_DEBUG", "false").lower() == "true"
    app.run(use_reloader=False, debug=debug, host=host, port=port)
