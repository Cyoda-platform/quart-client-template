import asyncio
import logging

from quart import Quart
from quart_schema import QuartSchema
from common.grpc_client.grpc_client import grpc_stream
from common.repository.cyoda.cyoda_init import init_cyoda
from app_init.app_init import cyoda_token
#please update this line to your entity
from entity.subscriber.api import api_bp_subscriber
from entity.send_fact.api import api_bp_send_fact
from entity.cat_fact.api import api_bp_cat_fact
from entity.subscriber_count.api import api_bp_subscriber_count
from entity.ENTITY_NAME_VAR.api import api_bp_ENTITY_NAME_VAR

logging.basicConfig(level=logging.INFO)

app = Quart(__name__)
QuartSchema(app)
app.register_blueprint(api_bp_subscriber, url_prefix='/api/subscriber')
app.register_blueprint(api_bp_send_fact, url_prefix='/api/send_fact')
app.register_blueprint(api_bp_cat_fact, url_prefix='/api/cat_fact')
app.register_blueprint(api_bp_subscriber_count, url_prefix='/api/subscriber_count')
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