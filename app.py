import asyncio
import logging

from quart import Quart
from quart_schema import QuartSchema
from common.grpc_client.grpc_client import grpc_stream
from common.repository.cyoda.cyoda_init import init_cyoda
from app_init.app_init import cyoda_token
#please update this line to your entity
from entity.flight_search.api import api_bp_flight_search
from entity.flight_favorite.api import api_bp_flight_favorite
from entity.flight.api import api_bp_flight
from entity.flight_filter.api import api_bp_flight_filter
from entity.ENTITY_NAME_VAR.api import api_bp_ENTITY_NAME_VAR

logging.basicConfig(level=logging.INFO)

app = Quart(__name__)
QuartSchema(app)
app.register_blueprint(api_bp_flight_search, url_prefix='/api/flight_search')
app.register_blueprint(api_bp_flight_favorite, url_prefix='/api/flight_favorite')
app.register_blueprint(api_bp_flight, url_prefix='/api/flight')
app.register_blueprint(api_bp_flight_filter, url_prefix='/api/flight_filter')
app.register_blueprint(api_bp_ENTITY_NAME_VAR, url_prefix='/api/ENTITY_NAME_VAR')

@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)
    app.background_task = asyncio.create_task(grpc_stream(cyoda_token))


@app.after_serving
async def shutdown():
    app.background_task.cancel()
    await app.background_task

#put_application_code_here

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)