import asyncio
import logging

from quart import Quart
from quart_schema import QuartSchema, ResponseSchemaValidationError, hide

from app_init.app_init import BeanFactory
from common.exception.exception_handler import register_error_handlers
# Import blueprints for different route groups
from routes.routes import routes_bp

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
factory = BeanFactory(config={"CHAT_REPOSITORY": "cyoda"})
grpc_client = factory.get_services()["grpc_client"]

app = Quart(__name__)

QuartSchema(app,
            info={"title": "Cyoda Client API", "version": "0.1.0"},
            tags=[{"name": "Cyoda Client", "description": "Cloud Client API: prototype"}],
            security=[{"bearerAuth": []}],
            security_schemes={
                "bearerAuth": {
                    "type": "http",
                    "scheme": "bearer",
                }
            })

# Register blueprints
app.register_blueprint(routes_bp)

# Register error handlers for custom and generic exceptions
@app.errorhandler(ResponseSchemaValidationError)
async def handle_response_validation_error():
    return {"error": "VALIDATION"}, 500

register_error_handlers(app)

@app.route("/favicon.ico")
@hide
def favicon():
    return "", 200
# Startup tasks: initialize Cyoda and start the GRPC stream in the background
@app.before_serving
async def startup():
    app.background_task = asyncio.create_task(grpc_client.grpc_stream())


# Shutdown tasks: cancel the background task when shutting down
@app.after_serving
async def shutdown():
    app.background_task.cancel()
    await app.background_task


# Middleware to add CORS headers to every response
@app.before_serving
async def add_cors_headers():
    @app.after_request
    async def apply_cors(response):
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "*"
        response.headers["Access-Control-Allow-Credentials"] = "true"
        return response


if __name__ == "__main__":
    app.run(use_reloader=False, debug=True, host="0.0.0.0", port=8000)
